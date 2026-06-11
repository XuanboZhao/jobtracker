"""Email digest of jobs that first appeared in the latest run.
Credentials come from environment variables (GitHub Secrets), never hardcoded:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_TO
"""
from __future__ import annotations
import os, smtplib
from email.message import EmailMessage


def send_digest(new_rows: list[dict]) -> bool:
    to = os.environ.get("MAIL_TO")
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    if not (to and user and pw):
        print("[notify] SMTP env not set — skipping email")
        return False
    if not new_rows:
        print("[notify] no new jobs — skipping email")
        return False

    lines = [f"{len(new_rows)} 个新岗位\n"]
    for r in new_rows:
        lines.append(f"• [{r['company']}] {r['title']} — {r.get('location','')}\n  {r['url']}")
    body = "\n".join(lines)

    msg = EmailMessage()
    msg["Subject"] = f"Job Desk · 今日新增 {len(new_rows)} 个岗位"
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP_SSL(host, port) as s:
        s.login(user, pw)
        s.send_message(msg)
    print(f"[notify] sent digest to {to}")
    return True
