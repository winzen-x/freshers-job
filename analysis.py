"""Fresher / internship detection from the job text, plus title and city matching."""
import re, html

CITIES = {"chennai": "Chennai", "bangalore": "Bangalore", "bengaluru": "Bangalore"}
FRESH = re.compile(r"\b(freshers?|fresh graduates?|graduates?|entry[- ]level|trainee|new grads?|campus|no experience|0\s*(?:-|–|to)\s*[12]\s*years?|0\s*years?)\b", re.I)
SENIOR = re.compile(r"\b(senior|sr\.?|lead|principal|staff|manager|head|director|architect|vp)\b", re.I)
YEARS = re.compile(r"(\d{1,2})\s*(?:\+|[-–]|to)?\s*(\d{1,2})?\s*\+?\s*(?:years?|yrs?)\b", re.I)

def norm(s): return " ".join(re.sub(r"[^a-z0-9+# ]", " ", (s or "").lower()).split())
def clean(t): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(html.unescape(t or ""))))

def city_of(location, want=""):
    """Return 'Chennai' / 'Bangalore' if the location is one of them (and matches `want` if given)."""
    low = (location or "").lower()
    for k, v in CITIES.items():
        if k in low and (not want or want == v): return v
    return None

def analyse(title, desc):
    """Return None if the job needs experience, else {kind, exp}."""
    text = f"{title}. {clean(desc)}"
    if SENIOR.search(title) or re.search(r"experienced professionals?", text, re.I): return None
    for m in YEARS.finditer(text):                       # "2+ years", "1-3 years", "minimum 1 year"...
        ctx = text[max(0, m.start() - 60): m.end() + 60].lower()
        if "experience" in ctx and int(m.group(1)) >= 1: return None   # "0-1 years" passes (starts at 0)
    kind = "Internship" if re.search(r"\bintern(ship)?s?\b", title, re.I) else "Fresher"
    return {"kind": kind, "exp": "Fresher-friendly" if FRESH.search(text) else "Experience not mentioned"}
