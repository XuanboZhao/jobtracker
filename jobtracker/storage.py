"""Persistence + the 'never forget while still open' logic.

Each run:
  - jobs seen today  -> upsert, last_seen=today, is_open=1 (new ones get first_seen=today)
  - jobs NOT seen today but previously open -> is_open=0, closed_at=today
Classification:
  - NEW      = is_open=1 AND first_seen within NEW_DAYS
  - ARCHIVE  = is_open=1 AND first_seen older than NEW_DAYS  (still in application period)
Application *status* is NOT stored here — it lives in the dashboard (window.storage),
so refreshing the feed never overwrites the user's progress.
"""
from __future__ import annotations
import sqlite3
from datetime import date, datetime, timedelta
from .models import JobRecord

NEW_DAYS = 7

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  company TEXT, company_category TEXT, title TEXT, url TEXT,
  location TEXT, department TEXT, job_category TEXT, seniority TEXT,
  posted_at TEXT, source_ats TEXT,
  first_seen TEXT, last_seen TEXT, is_open INTEGER, closed_at TEXT
);
"""


class Store:
    def __init__(self, path: str = "jobs.db"):
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    def sync(self, jobs: list[JobRecord], today: str | None = None) -> dict:
        today = today or date.today().isoformat()
        seen = set()
        added = []
        cur = self.con.cursor()
        for j in jobs:
            seen.add(j.id)
            row = cur.execute("SELECT id, first_seen FROM jobs WHERE id=?", (j.id,)).fetchone()
            if row is None:
                cur.execute(
                    """INSERT INTO jobs VALUES (:id,:company,:company_category,:title,:url,
                       :location,:department,:job_category,:seniority,:posted_at,:source_ats,
                       :fs,:fs,1,NULL)""",
                    {**j.to_dict(), "fs": today})
                added.append(j.id)
            else:
                cur.execute(
                    """UPDATE jobs SET last_seen=?, is_open=1, closed_at=NULL,
                       title=?, url=?, location=?, job_category=?, seniority=? WHERE id=?""",
                    (today, j.title, j.url, j.location, j.job_category, j.seniority, j.id))
        # close anything previously open that didn't show up today
        closed = []
        for row in cur.execute("SELECT id FROM jobs WHERE is_open=1").fetchall():
            if row["id"] not in seen:
                cur.execute("UPDATE jobs SET is_open=0, closed_at=? WHERE id=?", (today, row["id"]))
                closed.append(row["id"])
        self.con.commit()
        return {"added": added, "closed": closed, "seen": len(seen)}

    def open_jobs(self) -> list[dict]:
        rows = self.con.execute("SELECT * FROM jobs WHERE is_open=1 ORDER BY first_seen DESC").fetchall()
        return [dict(r) for r in rows]

    def new_jobs(self, today: str | None = None) -> list[dict]:
        cutoff = (datetime.fromisoformat(today or date.today().isoformat())
                  - timedelta(days=NEW_DAYS)).date().isoformat()
        rows = self.con.execute(
            "SELECT * FROM jobs WHERE is_open=1 AND first_seen >= ? ORDER BY first_seen DESC",
            (cutoff,)).fetchall()
        return [dict(r) for r in rows]
