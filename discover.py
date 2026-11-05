"""Finds which companies in company_names.txt publish jobs on a supported career-page system,
tests them, and adds the working ones (with Chennai/Bangalore jobs) to companies.json.

Run:  python discover.py            (adds companies that have Chennai/Bangalore jobs)
      python discover.py --keep-all (adds every company whose board exists)
"""
import json, re, sys, time, httpx

KEEP_ALL = "--keep-all" in sys.argv
URLS = {   # career-page feed for a guessed name ("slug"); a hit means the company uses that system
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{}/postings?limit=100",
}

def slugs(name):
    n = re.sub(r"[^a-z0-9 ]", "", name.lower().replace(".", "")).split()
    out = ["".join(n), "-".join(n), n[0]] if n else []
    return list(dict.fromkeys(out))          # unique, keep order

def has_jobs(ats, data):
    if ats == "greenhouse" or ats == "ashby": return bool(data.get("jobs"))
    if ats == "lever": return isinstance(data, list) and len(data) > 0
    return bool(data.get("totalFound"))

def main():
    names = [l.strip() for l in open("company_names.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
    try: found = json.load(open("companies.json", encoding="utf-8"))
    except Exception: found = []
    have = {(c["ats"], c["token"]) for c in found}
    with httpx.Client(timeout=15, headers={"User-Agent": "fresher-jobs-app"}) as client:
        for name in names:
            hit = False
            for ats, url in URLS.items():
                for slug in slugs(name):
                    time.sleep(0.25)                           # polite: ~4 requests per second
                    try:
                        r = client.get(url.format(slug))
                        if r.status_code != 200: continue
                        data = r.json()
                        if not has_jobs(ats, data): continue
                    except Exception: continue
                    text = json.dumps(data).lower()
                    n = sum(text.count(k) for k in ("chennai", "bengaluru", "bangalore"))
                    if (ats, slug) not in have and (n or KEEP_ALL):
                        found.append({"name": name, "ats": ats, "token": slug}); have.add((ats, slug))
                    print(f"FOUND {name:25} {ats}/{slug}  (Chennai/Bangalore mentions: {n})")
                    hit = True; break
                if hit: break
            if not hit: print(f"none  {name}")
    json.dump(found, open("companies.json", "w", encoding="utf-8"), indent=1)
    print(f"\nDone. companies.json now has {len(found)} companies.")

main()
