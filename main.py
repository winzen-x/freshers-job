"""Run:  uvicorn main:app --reload   ->  http://127.0.0.1:8000"""
import asyncio, csv, io, json, smtplib
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import config, db
from analysis import analyse, city_of, norm
from sources.ats import REGISTRY
from websearch import discover, TITLES

app = FastAPI(title="Fresher Jobs")

def companies(): return json.load(open("companies.json", encoding="utf-8"))

def parse_date(s):
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00")); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception: return None

async def run_search(p):
    q, want = norm(p["q"]), p.get("city", "")
    keep = lambda title, loc: q in norm(title) and city_of(loc, want)     # EXACT title phrase + city
    sem = asyncio.Semaphore(5)                                            # polite: max 5 requests at once
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "fresher-jobs-app"}) as client:
        async def one(c):
            async with sem: return await REGISTRY[c["ats"]](client, c, keep)
        cs = companies()
        res = await asyncio.gather(*[one(c) for c in cs], return_exceptions=True)
    jobs, errors, now = [], [], datetime.now(timezone.utc)
    for c, r in zip(cs, res):
        if isinstance(r, Exception): errors.append(f"{c['name']}: " + ("career-page name not found, fix or remove it in companies.json" if "404" in str(r) else str(r)[:80])); continue
        for j in r:
            a = analyse(j.title, j.description)
            if not a: continue
            if p.get("kind") and a["kind"] != p["kind"]: continue
            d = parse_date(j.posted)
            if p.get("days") and d and now - d > timedelta(days=p["days"]): continue
            jobs.append({**j.dict(), "description": "", "city": city_of(j.location), **a})
    jobs.sort(key=lambda j: j["posted"] or "", reverse=(p.get("sort", "date") == "date"))
    return jobs, errors

@app.get("/api/search")
async def search(q: str = Query(..., min_length=2), city: str = "", kind: str = "", days: int = 0, sort: str = "date", web: bool = False):
    note = ""
    if web:   # search the internet for more companies hiring for this title, then search their career pages
        try:
            n = await discover([f"{q} fresher intern {c}" for c in ([city] if city else ["Chennai", "Bangalore"])])
            note = f"{n} new companies found on the web. "
        except Exception as e: note = f"Web search skipped: {e}. "
    jobs, errors = await run_search({"q": q, "city": city, "kind": kind, "days": days, "sort": sort})
    return {"jobs": jobs, "errors": errors, "companies": len(companies()), "note": note}

@app.post("/api/discover")
async def find_companies():
    """Finds tech companies hiring in Chennai/Bangalore by running many web searches (uses ~16 search credits)."""
    try: n = await discover([f"{t} fresher intern {c}" for t in TITLES for c in ("Chennai", "Bangalore")])
    except Exception as e: raise HTTPException(400, str(e))
    return {"added": n, "total": len(companies())}

@app.get("/api/companies")
def list_companies(): return companies()

@app.get("/api/export")
async def export(q: str = Query(..., min_length=2), fmt: str = "csv", city: str = "", kind: str = "", days: int = 0):
    jobs, _ = await run_search({"q": q, "city": city, "kind": kind, "days": days})
    cols = ["title", "company", "city", "kind", "exp", "posted", "url"]
    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.append(cols)
        for j in jobs: ws.append([j[c] for c in cols])
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": "attachment; filename=jobs.xlsx"})
    buf = io.StringIO(); w = csv.writer(buf); w.writerow(cols)
    for j in jobs: w.writerow([j[c] for c in cols])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=jobs.csv"})

@app.get("/api/check")
async def check():
    """Tests every company in companies.json so you can see which boards work (wrong token = error)."""
    out = []
    async with httpx.AsyncClient(timeout=20) as client:
        for c in companies():
            try: n = len(await REGISTRY[c["ats"]](client, c, lambda t, l: True)) if c["ats"] != "smartrecruiters" else "ok"; out.append({"company": c["name"], "ok": True, "jobs": n})
            except Exception as e: out.append({"company": c["name"], "ok": False, "error": str(e)})
    return out

class Save(BaseModel): job: dict
class Update(BaseModel): status: str | None = None; notes: str | None = None

@app.get("/api/saved")
def saved(): return [{**r, "job": json.loads(r["job"])} for r in db.rows("SELECT * FROM saved ORDER BY id DESC")]
@app.post("/api/saved")
def save(b: Save): db.run("INSERT OR IGNORE INTO saved(url, job) VALUES(?,?)", b.job["url"], json.dumps(b.job)); return {"ok": True}
@app.patch("/api/saved/{id}")
def update(id: int, b: Update):
    if b.status is not None: db.run("UPDATE saved SET status=? WHERE id=?", b.status, id)
    if b.notes is not None: db.run("UPDATE saved SET notes=? WHERE id=?", b.notes, id)
    return {"ok": True}
@app.delete("/api/saved/{id}")
def unsave(id: int): db.run("DELETE FROM saved WHERE id=?", id); return {"ok": True}

@app.get("/api/alerts")
def alerts(): return [{"id": r["id"], "params": json.loads(r["params"])} for r in db.rows("SELECT * FROM alerts")]
@app.post("/api/alerts")
def add_alert(p: dict):
    if not p.get("q"): raise HTTPException(400, "q required")
    return {"id": db.run("INSERT INTO alerts(params) VALUES(?)", json.dumps(p))}
@app.delete("/api/alerts/{id}")
def del_alert(id: int): db.run("DELETE FROM alerts WHERE id=?", id); return {"ok": True}

def notify(title, body):
    try:
        from plyer import notification; notification.notify(title=title, message=body[:250], timeout=10)
    except Exception: pass
    if config.SMTP_HOST and config.ALERT_EMAIL_TO:
        m = EmailMessage(); m["Subject"], m["From"], m["To"] = title, config.SMTP_USER, config.ALERT_EMAIL_TO; m.set_content(body)
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s: s.starttls(); s.login(config.SMTP_USER, config.SMTP_PASS); s.send_message(m)

async def alert_loop():
    while True:
        for a in db.rows("SELECT * FROM alerts"):
            try:
                jobs, _ = await run_search(json.loads(a["params"]))
                seen = set(json.loads(a["seen"])); new = [j for j in jobs if j["url"] not in seen]
                if new and seen: notify(f"{len(new)} new fresher/intern jobs", "\n".join(f"{j['title']} - {j['company']}\n{j['url']}" for j in new[:10]))
                db.run("UPDATE alerts SET seen=? WHERE id=?", json.dumps([j["url"] for j in jobs]), a["id"])
            except Exception as e: print("alert error:", e)
        await asyncio.sleep(config.ALERT_INTERVAL_MIN * 60)

@app.on_event("startup")
async def start(): asyncio.create_task(alert_loop())
@app.get("/")
def index(): return FileResponse("static/index.html")
app.mount("/static", StaticFiles(directory="static"), name="static")
