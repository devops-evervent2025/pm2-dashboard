import datetime
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
from app.models import User, SecretRevealAudit, CurlCommandAudit, ProcessLogAudit
from app.otp_models import LoginOtp
from app.email_utils import send_email
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

def _clear_user_references(db: Session, user_id: int):
    """Before deleting a user, null out every FK column across the whole
    schema that references users.id - audit tables, created_by columns,
    anything. Discovers these from the database itself rather than a
    hardcoded table list, so it can't miss a table added later."""
    from sqlalchemy import inspect as sa_inspect, text

    engine = db.get_bind()
    inspector = sa_inspect(engine)
    for table_name in inspector.get_table_names():
        if table_name == "users":
            continue
        for fk in inspector.get_foreign_keys(table_name):
            if fk.get("referred_table") != "users":
                continue
            for local_col, remote_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                if remote_col == "id":
                    db.execute(
                        text(f"UPDATE {table_name} SET {local_col} = NULL WHERE {local_col} = :uid"),
                        {"uid": user_id},
                    )
    db.commit()


OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5


class LoginResponse(BaseModel):
    otp_required: bool = True
    username: str
    masked_email: str | None = None
    access_token: str | None = None
    role: str | None = None


OTP_GRACE_PERIOD = datetime.timedelta(hours=1)


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
    settings = get_settings()

    # When email OTP is switched off in .env, skip straight to a token -
    # same response shape (otp_required=False) the frontend already
    # handles for the "recently verified" grace-period case, so no
    # frontend change is needed for this toggle.
    if not settings.REQUIRE_EMAIL_OTP:
        token = create_access_token({"sub": user.username, "role": user.role.value})
        return LoginResponse(
            otp_required=False,
            username=user.username,
            access_token=token,
            role=user.role.value,
        )

    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no email on file - an admin must add one before you can sign in.",
        )

    # If this account completed OTP verification within the last hour,
    # skip asking again - password alone is enough within that window.
    now = datetime.datetime.utcnow()
    if user.last_otp_verified_at and (now - user.last_otp_verified_at) < OTP_GRACE_PERIOD:
        token = create_access_token({"sub": user.username, "role": user.role.value})
        return LoginResponse(
            otp_required=False,
            username=user.username,
            access_token=token,
            role=user.role.value,
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
        f"<p style=\"font-size:24px;font-weight:bold;letter-spacing:4px;\">{code}</p>"
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
    user.last_otp_verified_at = datetime.datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": user.username, "role": user.role.value})
    return Token(access_token=token, role=user.role, username=user.username)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(User).all()


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)

    demoting_self = user.id == admin.id and (
        ("role" in update_data and update_data["role"] != "admin")
        or ("is_active" in update_data and update_data["is_active"] is False)
    )
    if demoting_self:
        other_active_admins = (
            db.query(User)
            .filter(User.role == "admin", User.is_active == True, User.id != admin.id)
            .count()
        )
        if other_active_admins == 0:
            raise HTTPException(
                status_code=400,
                detail="You are the last active admin - promote another user to admin first.",
            )

    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        other_active_admins = (
            db.query(User)
            .filter(User.role == "admin", User.is_active == True, User.id != user.id)
            .count()
        )
        if other_active_admins == 0:
            raise HTTPException(status_code=400, detail="Cannot delete the last remaining admin.")

    # Clear every FK reference to this user across the whole schema first -
    # MySQL's default ON DELETE RESTRICT would otherwise block deleting any
    # user who's referenced anywhere (audit tables, created_by columns, etc).
    _clear_user_references(db, user.id)

    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}
