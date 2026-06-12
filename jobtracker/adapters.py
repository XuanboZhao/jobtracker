"""One adapter per ATS *type* (not per company). The config picks which one
runs for each company, so 10 Greenhouse companies share this one function.

Each adapter takes a company config dict and returns list[JobRecord].
"""
from __future__ import annotations
import requests
from .models import JobRecord

TIMEOUT = 20
HEADERS = {"User-Agent": "job-desk/0.1 (personal job tracker)"}

_NL_PATTERNS = [
    r"fluent\s+(?:in\s+)?dutch",
    r"dutch\s+(?:language|speaker|speaking|proficiency|skills?|required|mandatory)",
    r"native\s+dutch",
    r"professional\s+(?:proficiency\s+in\s+)?dutch",
    r"dutch\s+is\s+(?:required|mandatory|essential|a\s+must)",
    r"must\s+(?:speak|be\s+fluent\s+in)\s+dutch",
    r"vloeiend\s+(?:in\s+het\s+)?nederlands",
    r"nederlandse?\s+taal(?:vaardigheid)?",
    r"beheersing\s+van\s+(?:het\s+)?nederlands",
    r"je\s+spreekt\s+(?:vloeiend\s+)?nederlands",
]

def _check_dutch(html: str) -> bool | None:
    """Return True if text explicitly requires Dutch, False if description exists but no mention."""
    if not html:
        return None
    import re as _re
    text = _re.sub(r"<[^>]+>", " ", html).lower()
    return any(_re.search(p, text) for p in _NL_PATTERNS)


def _gid(ats: str, company: str, ext) -> str:
    return f"{ats}-{company}-{ext}".lower().replace(" ", "-")


def greenhouse(cfg: dict) -> list[JobRecord]:
    """Greenhouse Job Board API — public JSON, no auth.
    https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
    """
    token = cfg["token"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    r = requests.get(url, params={"content": "true"}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        loc = (j.get("location") or {}).get("name", "") or ""
        content = j.get("content") or ""
        dutch = _check_dutch(content)
        out.append(JobRecord(
            id=_gid("gh", cfg["name"], j["id"]),
            company=cfg["name"],
            company_category=cfg["category"],
            title=j.get("title", "").strip(),
            url=j.get("absolute_url", ""),
            location=loc,
            posted_at=(j.get("updated_at") or j.get("first_published") or "")[:10],
            source_ats="greenhouse",
            requires_dutch=dutch,
        ))
    return out


def lever(cfg: dict) -> list[JobRecord]:
    """Lever Postings API — public JSON, no auth.
    https://api.lever.co/v0/postings/{token}?mode=json
    """
    token = cfg["token"]
    url = f"https://api.lever.co/v0/postings/{token}"
    r = requests.get(url, params={"mode": "json"}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for j in r.json():
        cats = j.get("categories", {}) or {}
        content = (j.get("descriptionPlain") or j.get("description") or "")
        dutch = _check_dutch(content)
        out.append(JobRecord(
            id=_gid("lv", cfg["name"], j.get("id", j.get("text", ""))),
            company=cfg["name"],
            company_category=cfg["category"],
            title=j.get("text", "").strip(),
            url=j.get("hostedUrl", ""),
            location=cats.get("location", "") or "",
            department=cats.get("team", "") or "",
            posted_at=str(j.get("createdAt", ""))[:10],
            source_ats="lever",
            requires_dutch=dutch,
        ))
    return out


def workday(cfg: dict) -> list[JobRecord]:
    """Workday Job Board API — semi-public REST endpoint (POST), no auth.
    Config keys: workday_tenant, workday_instance (default wd3), workday_board
    """
    import re as _re
    from datetime import date as _date, timedelta as _td

    tenant   = cfg["workday_tenant"]
    instance = cfg.get("workday_instance", "wd3")
    board    = cfg["workday_board"]
    base     = f"https://{tenant}.{instance}.myworkdayjobs.com"
    api      = f"{base}/wday/cxs/{tenant}/{board}/jobs"

    def _parse_posted(text: str) -> str:
        if not text:
            return ""
        t = text.lower()
        today = _date.today()
        if "today" in t:
            return today.isoformat()
        m = _re.search(r"(\d+)\s+day", t)
        if m:
            return (_date.today() - _td(days=int(m.group(1)))).isoformat()
        m = _re.search(r"(\d+)\s+month", t)
        if m:
            return (_date.today() - _td(days=int(m.group(1)) * 30)).isoformat()
        return ""

    out, offset, limit = [], 0, 50
    while True:
        r = requests.post(
            api,
            json={"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""},
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for j in postings:
            path = j.get("externalPath", "")
            ext_id = path.split("/")[-1] if path else j.get("title", "")
            out.append(JobRecord(
                id=_gid("wd", cfg["name"], ext_id),
                company=cfg["name"],
                company_category=cfg["category"],
                title=j.get("title", "").strip(),
                url=base + path if path else "",
                location=j.get("locationsText", "") or "",
                posted_at=_parse_posted(j.get("postedOn", "")),
                source_ats="workday",
                requires_dutch=None,  # description requires per-job fetch; skipped for now
            ))
        if offset + limit >= data.get("total", 0):
            break
        offset += limit
    return out


def custom(cfg: dict) -> list[JobRecord]:
    """Placeholder for sites without a public feed.
    Returns nothing so the pipeline still runs cleanly with the others."""
    return []


REGISTRY = {"greenhouse": greenhouse, "lever": lever, "workday": workday, "custom": custom}


def fetch_company(cfg: dict) -> list[JobRecord]:
    fn = REGISTRY.get(cfg.get("ats"))
    if fn is None:
        raise ValueError(f"unknown ats type: {cfg.get('ats')}")
    return fn(cfg)
