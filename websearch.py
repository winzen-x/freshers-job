"""Searches the internet to discover companies that post jobs on their own career pages.
It searches the career-page sites (Lever, Greenhouse, Ashby, SmartRecruiters) for your title + city,
reads the company name out of each result link, and adds it to companies.json."""
import re, json, config

DOMAINS = ["jobs.lever.co", "boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.ashbyhq.com", "jobs.smartrecruiters.com"]
PATTERNS = [("greenhouse", r"greenhouse\.io/(?!embed)([A-Za-z0-9_-]+)"), ("lever", r"jobs\.lever\.co/([A-Za-z0-9_-]+)"),
            ("ashby", r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)"), ("smartrecruiters", r"jobs\.smartrecruiters\.com/([A-Za-z0-9_-]+)")]
TITLES = ["software engineer", "developer", "data analyst", "intern", "QA engineer", "devops engineer", "frontend developer", "backend developer"]

async def web(query):
    """Return a list of result URLs from whichever search key is configured."""
    import httpx
    async with httpx.AsyncClient(timeout=25) as c:
        if config.TAVILY_KEY:
            r = await c.post("https://api.tavily.com/search", json={"api_key": config.TAVILY_KEY, "query": query,
                             "max_results": 20, "include_domains": DOMAINS}); r.raise_for_status()
            return [x["url"] for x in r.json().get("results", [])]
        if config.BRAVE_KEY:
            q = "(" + " OR ".join("site:" + d for d in DOMAINS) + ") " + query
            r = await c.get("https://api.search.brave.com/res/v1/web/search", params={"q": q, "count": 20},
                            headers={"X-Subscription-Token": config.BRAVE_KEY}); r.raise_for_status()
            return [x["url"] for x in r.json().get("web", {}).get("results", [])]
    raise RuntimeError("No search key set. Set TAVILY_KEY (free at tavily.com) before starting the app.")

def extract(urls):
    """Career-page links -> [(ats, token)]. e.g. https://jobs.lever.co/cred/123 -> ('lever', 'cred')"""
    out = []
    for u in urls:
        for ats, rx in PATTERNS:
            m = re.search(rx, u)
            if m and (ats, m.group(1)) not in out: out.append((ats, m.group(1)))
    return out

async def discover(queries):
    """Run the searches, add new companies to companies.json, return how many were new."""
    try: cs = json.load(open("companies.json", encoding="utf-8"))
    except Exception: cs = []
    have = {(c["ats"], c["token"].lower()) for c in cs}; added = 0
    for q in queries:
        for ats, tok in extract(await web(q)):
            if (ats, tok.lower()) in have: continue
            cs.append({"name": tok.replace("-", " ").replace("_", " ").title(), "ats": ats, "token": tok})
            have.add((ats, tok.lower())); added += 1
    json.dump(cs, open("companies.json", "w", encoding="utf-8"), indent=1)
    return added
