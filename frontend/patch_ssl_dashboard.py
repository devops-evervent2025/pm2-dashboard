path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_import = "from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, nullslast"
new_import = "from sqlalchemy import Column, Integer, String, DateTime, ForeignKey"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("removed nullslast import")
else:
    print("MISSING: nullslast import line")

old_query = '''@router.get("/domains", response_model=List[SslDomainOut])
def list_domains(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    rows = db.query(SslDomain).order_by(nullslast(SslDomain.expires_at.asc())).all()'''

new_query = '''@router.get("/domains", response_model=List[SslDomainOut])
def list_domains(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    # MySQL has no NULLS LAST syntax - order by "is null" first (False < True,
    # so non-null rows sort first), then by the actual expiry date.
    rows = (
        db.query(SslDomain)
        .order_by(SslDomain.expires_at.is_(None), SslDomain.expires_at.asc())
        .all()
    )'''

if old_query in content:
    content = content.replace(old_query, new_query)
    changes.append("fixed order_by + made admin-only")
else:
    print("MISSING: list_domains function block")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
