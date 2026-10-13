"""Optional personal email delivery; never enabled without recipient configuration."""
import os
import ssl
import smtplib
from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage


def send_notifications(store, smtp_factory=None):
    host, sender, recipient = (os.getenv(key, "") for key in ("SMTP_HOST", "SMTP_FROM", "SMTP_TO"))
    if not all((host, sender, recipient)):
        return {"status": "disabled", "sent": 0}
    if any("\n" in value or "\r" in value for value in (host, sender, recipient)):
        return {"status": "configuration_error", "sent": 0}
    with store.connect() as db:
        today = datetime.now(ZoneInfo(store.preferences().get("reading_timezone", "Asia/Tokyo"))).date().isoformat()
        rows = db.execute("SELECT notifications.* FROM notifications JOIN bookmarks ON bookmarks.event_id=notifications.event_id JOIN events ON events.id=notifications.event_id WHERE notifications.read=0 AND notifications.emailed=0 AND bookmarks.status!='seen' AND coalesce(events.end_date,events.start_date)>=? ORDER BY notifications.created_at LIMIT 20", (today,)).fetchall()
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
