# Fresher Jobs (Chennai + Bangalore)

Finds fresher and internship jobs posted directly on tech companies' own career pages. No job portals.

## Run
```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000. Stop with Ctrl+C.

## How it works
- `companies.json` lists companies and which career-page system they use (greenhouse, lever, ashby, smartrecruiters).
- The app reads each company's public job feed, keeps only Chennai/Bangalore jobs whose title contains your exact title,
  drops anything asking 1+ years of experience or senior-level titles, and labels each job Fresher or Internship.
- Jobs that mention no experience are kept and labelled "Experience not mentioned".

## Add a company
1. Open the company's careers page and look at a job URL:
   - `boards.greenhouse.io/NAME/...` or `job-boards.greenhouse.io/NAME` -> ats `greenhouse`, token `NAME`
   - `jobs.lever.co/NAME` -> `lever` | `jobs.ashbyhq.com/NAME` -> `ashby` | `jobs.smartrecruiters.com/NAME` -> `smartrecruiters`
2. Add `{"name": "...", "ats": "...", "token": "..."}` to `companies.json` and restart.
3. Visit http://127.0.0.1:8000/api/check to see which companies respond. Wrong tokens show as errors.

Companies with their own custom careers site (Zoho, for example) cannot be read this way.

## Find many more companies automatically
```
python discover.py
```
It checks every name in `company_names.txt` against all four career-page systems, and adds the ones that work
(and have Chennai/Bangalore jobs) to `companies.json`. Takes a few minutes. Add your own names to the file and run it again.
Use `python discover.py --keep-all` to also keep companies with no Chennai/Bangalore jobs right now.

## Search the internet for companies (like Google)
1. Get a free key at https://tavily.com (no card) and copy it.
2. In cmd, before starting the app:  `set TAVILY_KEY=your_key_here`   (Windows)  |  `export TAVILY_KEY=your_key_here` (Mac/Linux)
3. Start the app. With "Search the internet for new companies" ticked, every search first finds new companies
   hiring for your title, adds them, then reads their job feeds. The **Companies** tab has a button to find all
   Chennai + Bangalore tech companies at once.
