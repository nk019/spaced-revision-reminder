import smtplib
from email.mime.text import MIMEText as _MIMEText_Fallback  # fallback if import below fails
try:
    from email.mime.text import MIMEText
except Exception:
    MIMEText = _MIMEText_Fallback
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from plyer import notification
from dotenv import dotenv_values
from typing import Optional
import pytz
from db import SessionLocal
from models import Reminder

ENV = dotenv_values(".env")
def _send_email(subject: str, body: str) -> None:
    host = ENV.get("SMTP_HOST"); port = ENV.get("SMTP_PORT")
    user = ENV.get("SMTP_USER");  pwd  = ENV.get("SMTP_PASS")
    from_addr = ENV.get("SMTP_FROM"); to_addr = ENV.get("SMTP_TO")
    if not all([host, port, user, pwd, from_addr, to_addr]):
        return
    msg = MIMEText(body); msg["Subject"]=subject; msg["From"]=from_addr; msg["To"]=to_addr
    with smtplib.SMTP(host, int(port)) as server:
        server.starttls(); server.login(user, pwd); server.sendmail(from_addr, [to_addr], msg.as_string())
def _desktop_notify(title: str, message: str) -> None:
    try: notification.notify(title=title, message=message, timeout=10)
    except Exception: pass
def _now_ist() -> datetime:
    tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).replace(tzinfo=None)
def dispatch_notifications(db: Session) -> int:
    # Find due reminders that haven't been notified and dispatch notifications.
    now = _now_ist(); count = 0
    q = db.query(Reminder).filter(Reminder.status=="pending", Reminder.notified==False)
    for rem in q.all():
        fire_time = rem.due_datetime - timedelta(minutes=rem.notify_minutes_before or 0)
        if fire_time <= now:
            title = f"Reminder: {rem.task.title}"
            when = rem.due_datetime.strftime("%Y-%m-%d %H:%M")
            body  = f"Task: {rem.task.title}\nWhen: {when}\nNotes: {rem.task.notes or '-'}"
            _desktop_notify(title, body); _send_email(title, body)
            rem.notified = True; db.add(rem); count += 1
    if count: db.commit()
    return count
_scheduler: Optional[BackgroundScheduler] = None
def start_scheduler():
    global _scheduler
    if _scheduler: return _scheduler
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(lambda: _job_wrapper(), 'interval', seconds=60, id="notify-job", replace_existing=True)
    _scheduler.start(); return _scheduler
def _job_wrapper():
    db = SessionLocal()
    try: dispatch_notifications(db)
    finally: db.close()
