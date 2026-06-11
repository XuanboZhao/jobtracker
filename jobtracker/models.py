"""The canonical record. Every adapter maps its raw payload into this shape,
so everything downstream (filter, store, export) is ATS-agnostic."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field


@dataclass
class JobRecord:
    id: str                 # stable, unique: f"{ats}-{company}-{external_id}"
    company: str
    company_category: str
    title: str
    url: str
    location: str = ""
    department: str = ""
    job_category: str = "Other"   # filled by classify.py
    seniority: str = "Experienced"
    posted_at: str = ""           # ATS-provided date if any (ISO)
    source_ats: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
