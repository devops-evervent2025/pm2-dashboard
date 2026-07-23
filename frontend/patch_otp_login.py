path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/auth.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_imports = '''from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import authenticate_user, create_access_token, get_current_user, require_admin, hash_password, AccountLockedError
from app.schemas import Token, UserOut, UserCreate, UserUpdate
from app.models import User'''

new_imports = '''import datetime
import random

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import (
    authenticate_user, create_access_token, get_current_user, require_admin,
    hash_password, verify_password, AccountLockedError,
)
from app.schemas import Token, UserOut, UserCreate, UserUpdate
from app.models import User
from app.otp_models import LoginOtp
from app.email_utils import send_email'''

if old_imports in content:
    content = content.replace(old_imports, new_imports)
    changes.append("imports updated")
else:
    print("MISSING: imports block")

old_login = '''@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
    except AccountLockedError as exc:
        minutes = exc.retry_after_seconds // 60
        seconds = exc.retry_after_seconds % 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": f"Too many failed attempts. Account locked for {minutes}m {seconds}s.",
                "retry_after_seconds": exc.retry_after_seconds,
            },
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return Token(access_token=token, role=user.role, username=user.username)'''

new_login = '''OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5


class LoginResponse(BaseModel):
    otp_required: bool = True
    username: str
    masked_email: str | None = None


class OtpVerifyRequest(BaseModel):
    username: str
    code: str


def _mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


@router.post("/login", response_model=LoginResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Step 1 of login: verifies username+password (same lockout logic as
    before), then - instead of returning a JWT directly - emails a 6-digit
    one-time code to the user's registered address. The JWT is only
    issued after that code is confirmed via /auth/otp/verify.
    """
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
    except AccountLockedError as exc:
        minutes = exc.retry_after_seconds // 60
        seconds = exc.retry_after_seconds % 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": f"Too many failed attempts. Account locked for {minutes}m {seconds}s.",
                "retry_after_seconds": exc.retry_after_seconds,
            },
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no email on file - an admin must add one before you can sign in.",
        )

    code = f"{random.randint(0, 999999):06d}"
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)

    db.add(LoginOtp(
        user_id=user.id,
        code_hash=hash_password(code),
        expires_at=expires_at,
        attempts=0,
        used=False,
    ))
    db.commit()

    sent = send_email(
        [user.email],
        "[PM2 Dashboard] Your sign-in code",
        f"<p>Your PM2 Dashboard sign-in code is:</p>"
        f"<p style=\\"font-size:24px;font-weight:bold;letter-spacing:4px;\\">{code}</p>"
        f"<p>This code expires in {OTP_EXPIRY_MINUTES} minutes. If you didn't try to sign in, you can ignore this email.</p>",
    )
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the verification email. Please try again or contact an admin.",
        )

    return LoginResponse(otp_required=True, username=user.username, masked_email=_mask_email(user.email))


@router.post("/otp/verify", response_model=Token)
def verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)):
    """Step 2 of login: checks the emailed code and, if valid, issues the
    real JWT - exactly what /auth/login used to return directly."""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid username or code")

    otp = (
        db.query(LoginOtp)
        .filter(LoginOtp.user_id == user.id, LoginOtp.used == False)
        .order_by(LoginOtp.id.desc())
        .first()
    )
    if not otp:
        raise HTTPException(status_code=400, detail="No pending code for this account - please sign in again.")

    now = datetime.datetime.utcnow()
    if otp.expires_at < now:
        raise HTTPException(status_code=400, detail="This code has expired - please sign in again.")

    if otp.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many incorrect attempts - please sign in again.")

    if not verify_password(payload.code.strip(), otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect code")

    otp.used = True
    db.commit()

    token = create_access_token({"sub": user.username, "role": user.role.value})
    return Token(access_token=token, role=user.role, username=user.username)'''

if old_login in content:
    content = content.replace(old_login, new_login)
    changes.append("login split into two-step OTP flow")
else:
    print("MISSING: old login function")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
