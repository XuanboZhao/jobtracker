"""Run the whole thing: python -m jobtracker.pipeline

  fetch (per company, isolated)  ->  filter  ->  store (diff)  ->  export  ->  notify
"""
from __future__ import annotations
import json, sys, traceback
from datetime import date
from pathlib import Path
import yaml

from .adapters import fetch_company
from .classify import classify
from .storage import Store, NEW_DAYS

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "config"
OUT = ROOT / "docs" / "data.json"


def load_yaml(p): return yaml.safe_load(p.read_text(encoding="utf-8"))


def keyword_filter(job, f) -> bool:
    title = job.title.lower()
    hay = title + (" " + job.location.lower() if f.get("match_in") == "title_and_location" else "")
    kws = [k.lower() for k in f.get("keywords", [])]
    if kws and not any(k in hay for k in kws):
        return False
    for ex in f.get("exclude_keywords", []) or []:
        if ex.lower() in title:
            return False
    loc_req = f.get("location_contains") or []
    if loc_req and not any(l.lower() in job.location.lower() for l in loc_req):
        return False
    sen_req = f.get("seniority_in") or []
    if sen_req and job.seniority not in sen_req:
        return False
    return True


def run():
    companies = load_yaml(CONF / "companies.yaml")["companies"]
    filters = load_yaml(CONF / "filters.yaml")
    today = date.today().isoformat()

    collected = []
    for c in companies:
        if not c.get("enabled", False):
            print(f"[skip] {c['name']} (disabled)")
            continue
        try:
            raw = fetch_company(c)
            kept = [classify(j) for j in raw]
            kept = [j for j in kept if keyword_filter(j, filters)]
            print(f"[ok]  {c['name']}: {len(raw)} fetched -> {len(kept)} matched")
            collected.extend(kept)
        except Exception as e:                       # one company failing never kills the run
            print(f"[err] {c['name']}: {e}")
            traceback.print_exc()

    store = Store(str(ROOT / "jobs.db"))
    diff = store.sync(collected, today)
    print(f"[store] +{len(diff['added'])} new, -{len(diff['closed'])} closed, {diff['seen']} open")

    open_rows = store.open_jobs()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"generated_at": today, "new_days": NEW_DAYS,
         "jobs": [{**r, "is_open": bool(r["is_open"])} for r in open_rows]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[export] wrote {len(open_rows)} open jobs -> {OUT}")

    try:
        from .notify import send_digest
        send_digest(store.new_jobs(today))
    except Exception as e:
        print(f"[notify] failed: {e}")


if __name__ == "__main__":
    sys.exit(run())
