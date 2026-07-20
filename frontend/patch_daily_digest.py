path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/notifications.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Remove the real-time email call from get_notification_summary (bell stays real-time, email does not)
old_call = '''    try:
        _send_new_alert_emails(db, process_alerts, ssl_alerts)
    except Exception as exc:
        import logging
        logging.getLogger("notifications").warning(f"[email] alert email dispatch failed: {exc}")

    summary = NotificationSummary('''

new_call = '''    summary = NotificationSummary('''

if old_call in content:
    content = content.replace(old_call, new_call)
    changes.append("real-time email trigger removed from /summary")
else:
    print("MISSING: real-time email trigger block")

# 2. Add the daily-digest background scheduler, right before the /summary endpoint
marker = '@router.get("/summary", response_model=NotificationSummary)'

digest_code = '''import datetime as _dt
import threading as _threading
import time as _time


def _send_daily_digest():
    """
    Sends ONE combined email at ~09:00 IST every day, listing every
    currently-active alert (errored processes + SSL certs expiring within
    24h) - regardless of whether each one was already emailed before.
    This is a summary/reminder digest, separate from - and replacing -
    any real-time per-alert email.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        recipients = [r.email for r in db.query(NotificationRecipient).all()]
        if not recipients:
            return

        process_alerts = _collect_process_alerts(db)
        ssl_alerts = _collect_ssl_alerts(db)

        if not process_alerts and not ssl_alerts:
            return  # nothing to report today

        rows = []
        for a in ssl_alerts:
            hours_txt = (
                "already expired" if (a.hours_remaining or 0) < 0
                else f"expires in {a.hours_remaining:.1f}h"
            )
            rows.append(
                f"<li><strong>{a.domain}</strong> ({a.client_name or 'Unknown client'}) - {hours_txt}</li>"
            )
        for a in process_alerts:
            rows.append(
                f"<li><strong>{a.process_name}</strong> on {a.server_name} "
                f"({a.client_name}) - {a.status}</li>"
            )

        subject = f"[PM2 Dashboard] Daily alert digest - {len(rows)} item(s) need attention"
        body = "<p>Here's today's summary of active alerts:</p><ul>" + "".join(rows) + "</ul>"
        send_email(recipients, subject, body)
    finally:
        db.close()


def _run_daily_digest_scheduler():
    """Background loop: checks every minute whether it's ~09:00 IST, and
    if so (and we haven't already sent today), sends the digest. Checking
    every minute rather than sleeping until exactly 9am keeps this simple
    and resilient to the process being restarted at any time of day."""
    last_sent_date = None
    while True:
        now = _dt.datetime.now()
        if now.hour == 9 and now.minute == 0 and last_sent_date != now.date():
            try:
                _send_daily_digest()
            except Exception:
                pass
            last_sent_date = now.date()
        _time.sleep(30)


def start_daily_digest_scheduler():
    thread = _threading.Thread(target=_run_daily_digest_scheduler, daemon=True)
    thread.start()


''' + marker

if marker in content and "_send_daily_digest" not in content:
    content = content.replace(marker, digest_code)
    changes.append("daily digest scheduler added")
else:
    print("MISSING or already present: /summary endpoint marker")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
