"""
Run standalone with:  python -m app.init_db
Also invoked automatically on FastAPI startup (see main.py).
Creates all tables and seeds a default admin user from .env if none exists.
"""
from app.database import Base, engine, SessionLocal
from app.models import User, RoleEnum
from app.auth import hash_password
from app.config import get_settings

settings = get_settings()


def bootstrap_admin():
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == RoleEnum.admin).first()
        if existing_admin:
            return
        admin = User(
            username=settings.DEFAULT_ADMIN_USERNAME,
            email=settings.DEFAULT_ADMIN_EMAIL,
            hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            role=RoleEnum.admin,
        )
        db.add(admin)
        db.commit()
        print(f"[init_db] Created default admin user '{admin.username}'. "
              f"Please log in and change the password immediately.")
    finally:
        db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    bootstrap_admin()
    print("[init_db] Database initialized.")
