path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/auth.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_response_model = '''class LoginResponse(BaseModel):
    otp_required: bool = True
    username: str
    masked_email: str | None = None'''

new_response_model = '''class LoginResponse(BaseModel):
    otp_required: bool = True
    username: str
    masked_email: str | None = None
    access_token: str | None = None
    role: str | None = None


OTP_GRACE_PERIOD = datetime.timedelta(hours=1)'''

if old_response_model in content:
    content = content.replace(old_response_model, new_response_model)
    changes.append("LoginResponse extended + grace period constant added")
else:
    print("MISSING: LoginResponse model")

old_body = '''    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no email on file - an admin must add one before you can sign in.",
        )

    code = f"{random.randint(0, 999999):06d}"'''

new_body = '''    if not user.email:
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

    code = f"{random.randint(0, 999999):06d}"'''

if old_body in content:
    content = content.replace(old_body, new_body)
    changes.append("grace-period skip logic added to login")
else:
    print("MISSING: login body tail")

old_verify_success = '''    otp.used = True
    db.commit()

    token = create_access_token({"sub": user.username, "role": user.role.value})
    return Token(access_token=token, role=user.role, username=user.username)'''

new_verify_success = '''    otp.used = True
    user.last_otp_verified_at = datetime.datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": user.username, "role": user.role.value})
    return Token(access_token=token, role=user.role, username=user.username)'''

if old_verify_success in content:
    content = content.replace(old_verify_success, new_verify_success)
    changes.append("verify_otp records last_otp_verified_at")
else:
    print("MISSING: verify_otp success block")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
