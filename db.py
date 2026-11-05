import sqlite3
con = sqlite3.connect("jobs.db", check_same_thread=False); con.row_factory = sqlite3.Row
con.executescript("""
CREATE TABLE IF NOT EXISTS saved(id INTEGER PRIMARY KEY, url TEXT UNIQUE, job TEXT, status TEXT DEFAULT 'Saved', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, params TEXT, seen TEXT DEFAULT '[]');""")
def rows(sql, *a): return [dict(r) for r in con.execute(sql, a)]
def run(sql, *a): cur = con.execute(sql, a); con.commit(); return cur.lastrowid
