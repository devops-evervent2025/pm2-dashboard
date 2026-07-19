path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/notifications.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_import = "from app.notification_models import NotificationRecipient"
new_import = "from app.notification_models import NotificationRecipient, NotificationSentLog\nfrom app.email_utils import send_email"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("imports added")
else:
    print("MISSING: NotificationRecipient import line")

marker = "@router.get(\"/summary\", response_model=NotificationSummary)"

email_helpers = '''def _send_new_alert_emails(db: Session, process_alerts: List[ProcessNotification], ssl_alerts: List[SslNotification]):
    """
    Sends ONE email per genuinely NEW alert (never seen before in
    notification_sent_log), then records it so it's never re-emailed
    while it remains active. If the alert later disappears (resolved)
    and then reappears, it's treated as new again (log entry only
    exists while the alert was first seen, we don't clear it on
    resolution - a resurfaced alert genuinely deserves a fresh email).
    """
    recipients = [r.email for r in db.query(NotificationRecipient).all()]
    if not recipients:
        return

    for a in process_alerts:
        key = f"process:{a.server_id}:{a.process_name}:{a.status}"
        if db.query(NotificationSentLog).filter(NotificationSentLog.alert_key == key).first():
            continue
        subject = f"[PM2 Dashboard] {a.process_name} is {a.status}"
        body = (
            f"<p><strong>{a.process_name}</strong> on <strong>{a.server_name}</strong> "
            f"({a.client_name}) is currently <strong>{a.status}</strong>.</p>"
            f"<p>Check the Alerts page in PM2 Dashboard for details.</p>"
        )
        if send_email(recipients, subject, body):
            db.add(NotificationSentLog(alert_key=key, alert_type="process"))
            db.commit()

    for a in ssl_alerts:
        key = f"ssl:{a.server_id}:{a.domain}"
        if db.query(NotificationSentLog).filter(NotificationSentLog.alert_key == key).first():
            continue
        hours_txt = (
            "already expired" if (a.hours_remaining or 0) < 0
            else f"expires in {a.hours_remaining:.1f} hours"
        )
        subject = f"[PM2 Dashboard] SSL certificate expiring soon: {a.domain}"
        body = (
            f"<p>The SSL certificate for <strong>{a.domain}</strong> "
            f"({a.client_name or 'Unknown client'}) {hours_txt}.</p>"
            f"<p>Check the SSL Certificates page in PM2 Dashboard for details.</p>"
        )
        if send_email(recipients, subject, body):
            db.add(NotificationSentLog(alert_key=key, alert_type="ssl"))
            db.commit()


''' + marker

if marker in content and "_send_new_alert_emails" not in content:
    content = content.replace(marker, email_helpers)
    changes.append("email trigger helper added")
else:
    print("MISSING or already present: summary endpoint marker")

old_summary_body = '''    process_alerts = _collect_process_alerts(db)
    ssl_alerts = _collect_ssl_alerts(db)

    summary = NotificationSummary('''

new_summary_body = '''    process_alerts = _collect_process_alerts(db)
    ssl_alerts = _collect_ssl_alerts(db)

    try:
        _send_new_alert_emails(db, process_alerts, ssl_alerts)
    except Exception as exc:
        import logging
        logging.getLogger("notifications").warning(f"[email] alert email dispatch failed: {exc}")

    summary = NotificationSummary('''

if old_summary_body in content:
    content = content.replace(old_summary_body, new_summary_body)
    changes.append("email dispatch wired into summary endpoint")
else:
    print("MISSING: summary endpoint body")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
