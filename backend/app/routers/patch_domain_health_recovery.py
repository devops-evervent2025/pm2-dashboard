import shutil
from datetime import datetime

path = "domain_health.py"
backup = f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
shutil.copy(path, backup)
print(f"Backed up to {backup}")

with open(path) as f:
    content = f.read()

changes = []

# 1. New recovery-email helper, placed right after _send_domain_down_email
old = '''def _check_and_store_domain_health(db: Session):'''
new = '''def _send_domain_recovered_email(db: Session, server_name, client_name, domain: str, last_status_code: int):
    admins = _get_admin_emails(db)
    if not admins:
        return
    subject = f"[PM2 Dashboard] {domain} is back up"
    body = (
        f"<p><strong>{domain}</strong>"
        f"{f' on {server_name}' if server_name else ''}"
        f"{f' ({client_name})' if client_name else ''} "
        f"has recovered - it was previously returning HTTP {last_status_code}, "
        f"now responding normally.</p>"
        f"<p>Check the SSL / Domains dashboard in PM2 Dashboard for details.</p>"
    )
    send_email(admins, subject, body)


def _check_and_store_domain_health(db: Session):'''
changes.append((old, new))

# 2. Send the recovery email once, right before deleting the resolved issue row
old = '''    # Recovered - no longer in the bad set, remove the issue row.
    for domain, existing in existing_issues.items():
        if domain not in bad_this_cycle:
            logger.info(f"[domain_health] recovered: {domain} - clearing issue")
            db.delete(existing)
    db.commit()'''
new = '''    # Recovered - no longer in the bad set. Send exactly one "back up"
    # email, then remove the issue row (a future recurrence is treated as
    # new and alerts again, same one-email-per-state-change principle as
    # the down alert).
    for domain, existing in existing_issues.items():
        if domain not in bad_this_cycle:
            srv = servers.get(existing.server_id)
            srv_name = srv.name if srv else None
            cli_name = clients.get(srv.client_id) if srv else None
            logger.info(f"[domain_health] recovered: {domain} - clearing issue")
            _send_domain_recovered_email(db, srv_name, cli_name, domain, existing.status_code)
            db.delete(existing)
    db.commit()'''
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
