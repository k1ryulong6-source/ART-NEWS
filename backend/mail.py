"""Optional personal email delivery; never enabled without recipient configuration."""
import os
import ssl
import smtplib
from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from .timing import instant_passed


def send_notifications(store, smtp_factory=None):
    host, sender, recipient = (os.getenv(key, "") for key in ("SMTP_HOST", "SMTP_FROM", "SMTP_TO"))
    if not all((host, sender, recipient)):
        return {"status": "disabled", "sent": 0}
    if any("\n" in value or "\r" in value for value in (host, sender, recipient)):
        return {"status": "configuration_error", "sent": 0}
    with store.connect() as db:
        rows = db.execute("SELECT notifications.*, events.timezone AS event_timezone, events.deadline_at, events.start_at, events.time_status, events.event_type, coalesce(events.end_date,events.start_date) AS last_day FROM notifications JOIN bookmarks ON bookmarks.event_id=notifications.event_id JOIN events ON events.id=notifications.event_id WHERE notifications.read=0 AND notifications.emailed=0 AND bookmarks.status!='seen' ORDER BY notifications.created_at").fetchall()
        eligible = []
        for row in rows:
            today = datetime.now(ZoneInfo(row["event_timezone"])).date().isoformat()
            if instant_passed(dict(row)) or row["last_day"] < today:
                continue
            if row["event_type"] == "call_deadline" and row["time_status"] == "conflict" and row["last_day"] == today:
                continue
            eligible.append(row)
        rows = eligible[:20]
    if not rows:
        return {"status": "idle", "sent": 0}
    message = EmailMessage()
    message["Subject"] = "映间：你收藏的活动即将开始或结束"
    message["From"], message["To"] = sender, recipient
    message.set_content("你收藏的活动有新的时间提醒：\n\n" + "\n".join(row["title"] for row in rows) + "\n\n开放时间与预约请以官方原文为准。")
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        factory = smtp_factory or (smtplib.SMTP_SSL if port == 465 else smtplib.SMTP)
        with factory(host, port, timeout=20) as client:
            if port != 465:
                client.starttls(context=ssl.create_default_context())
            if os.getenv("SMTP_USER"):
                client.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
            client.send_message(message)
        with store.connect() as db:
            db.executemany("UPDATE notifications SET emailed=1 WHERE id=?", [(row["id"],) for row in rows])
        return {"status": "sent", "sent": len(rows)}
    except Exception as exc:
        return {"status": "failed", "sent": 0, "error": type(exc).__name__}
