"""Lightweight title-based classification. Tune the keyword lists freely."""
from __future__ import annotations
import re
from .models import JobRecord

CATEGORY_RULES = [
    ("Quant",   [r"quant", r"researcher", r"research scientist"]),
    ("Trading", [r"\btrader\b", r"trading"]),
    ("Data",    [r"data scien", r"data engineer", r"machine learning", r"\bml\b", r"\bai\b", r"analytics"]),
    ("SWE",     [r"software", r"\bengineer\b", r"developer", r"\bswe\b", r"c\+\+", r"fpga", r"infrastructure"]),
    ("Risk",    [r"\brisk\b", r"compliance"]),
    ("Finance", [r"finance", r"investment", r"portfolio", r"analyst", r"\bcfa\b"]),
]

SENIORITY_RULES = [
    ("Intern",   [r"intern", r"internship", r"placement", r"working student"]),
    ("Graduate", [r"graduate", r"\bgrad\b", r"campus", r"junior", r"entry.level", r"new grad"]),
    # default -> Experienced
]


def _first_match(text: str, rules) -> str | None:
    for label, pats in rules:
        if any(re.search(p, text) for p in pats):
            return label
    return None


def classify(job: JobRecord) -> JobRecord:
    t = job.title.lower()
    job.job_category = _first_match(t, CATEGORY_RULES) or "Other"
    job.seniority = _first_match(t, SENIORITY_RULES) or "Experienced"
    return job
