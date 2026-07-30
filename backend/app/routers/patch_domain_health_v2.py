import shutil
from datetime import datetime

path = "domain_health.py"
backup = f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
shutil.copy(path, backup)
print(f"Backed up to {backup}")

with open(path) as f:
    content = f.read()

changes = []

# 1. Drop 404 from the alert set - too many false positives on API-only
#    domains that don't define a route at "/".
old = 'ALERT_STATUS_CODES = {500, 502, 404, 403}'
new = 'ALERT_STATUS_CODES = {500, 502, 403}'
changes.append((old, new))

# 2. Import NotificationRecipient
old = 'from app.models import User, Server, Client, RoleEnum'
new = 'from app.models import User, Server, Client, RoleEnum\nfrom app.notification_models import NotificationRecipient'
changes.append((old, new))

# 3. Recipients = intersection of admin-role users AND the recipients list
#    (not just "all admins", and not just "all recipients" - both).
old = '''def _get_admin_emails(db: Session) -> List[str]:
    rows = (
        db.query(User)
        .filter(User.role == RoleEnum.admin, User.email.isnot(None), User.email != "")
        .all()
    )
    return [u.email for u in rows]'''
new = '''def _get_admin_emails(db: Session) -> List[str]:
    """Admin-role users whose email address is ALSO present in the
    Email Notification Recipients list - i.e. removing someone from that
    recipients list stops domain-health emails to them too, same as it
    already does for PM2/SSL alerts."""
    admin_emails = {
        u.email for u in db.query(User)
        .filter(User.role == RoleEnum.admin, User.email.isnot(None), User.email != "")
        .all()
    }
    recipient_emails = {r.email for r in db.query(NotificationRecipient).all()}
    return sorted(admin_emails & recipient_emails)'''
changes.append((old, new))

for old, new in changes:
    count = content.count(old)
    if count != 1:
        print(f"ERROR: expected 1 occurrence, found {count}. Aborting, nothing changed. Block:\\n{old[:120]}")
        raise SystemExit(1)

for old, new in changes:
    content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)
print("Patched domain_health.py successfully.")
