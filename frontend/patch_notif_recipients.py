path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/notifications.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_imports = "from app.models import User, Server, Client"
new_imports = '''from app.models import User, Server, Client
from app.auth import require_admin
from app.notification_models import NotificationRecipient'''
if old_imports in content:
    content = content.replace(old_imports, new_imports)
    changes.append("imports added")
else:
    print("MISSING: models import line")

marker = "@router.get(\"/summary\", response_model=NotificationSummary)"

new_endpoints = '''class RecipientCreate(BaseModel):
    email: str


class RecipientOut(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


@router.get("/recipients", response_model=List[RecipientOut])
def list_recipients(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(NotificationRecipient).order_by(NotificationRecipient.email.asc()).all()


@router.post("/recipients", response_model=RecipientOut)
def add_recipient(
    payload: RecipientCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="That doesn't look like a valid email address.")

    existing = db.query(NotificationRecipient).filter(NotificationRecipient.email == email).first()
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="This email is already in the recipient list.")

    row = NotificationRecipient(email=email)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/recipients/{recipient_id}")
def delete_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    row = db.query(NotificationRecipient).filter(NotificationRecipient.id == recipient_id).first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Recipient not found")
    db.delete(row)
    db.commit()
    return {"detail": "Recipient removed"}


''' + marker

if marker in content and "/recipients" not in content:
    content = content.replace(marker, new_endpoints)
    changes.append("recipient endpoints added")
else:
    print("MISSING or already present: summary endpoint marker")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
