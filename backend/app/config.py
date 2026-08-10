"""
All configuration is sourced from environment variables (.env file).
Nothing is hardcoded - see .env.example for the full list of options.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "PM2 Dashboard"
    ENVIRONMENT: str = "Other"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # MySQL
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Default admin bootstrap
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"

    # Email OTP verification - when False, login is username+password
    # only and the /auth/otp/verify step is skipped entirely, no email
    # is sent. When True (default), the existing 2-step flow applies.
    REQUIRE_EMAIL_OTP: bool = True

    # SSH defaults
    SSH_DEFAULT_PORT: int = 22
    SSH_DEFAULT_USERNAME: str = "root"
    SSH_CONNECT_TIMEOUT: int = 10
    SSH_PRIVATE_KEY_PATH: str = ""

    # InfraLink Agent (optional Agent-based host management, alongside SSH).
    # False by default: when False, all InfraLink UI/API/WebSocket surfaces
    # are disabled and SSH behavior is completely unchanged.
    AGENT_ENABLED: bool = False

    # Base directory containing your repos/projects, e.g. /var/www/fullstack
    # Used ONLY by the admin-only repo/.env browser feature. The backend
    # will never read outside this directory.
    REPOS_BASE_DIR: str = "/var/www"

    # SMTP (for the email-notification feature) - leave SMTP_HOST empty
    # to disable email sending entirely (in-app notifications still work).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True
    # MaxScale (replication monitoring) - leave MAXSCALE_API_URL empty to
    # disable replication monitoring entirely.
    MAXSCALE_API_URL: str = ""
    MAXSCALE_API_USERNAME: str = ""
    MAXSCALE_API_PASSWORD: str = ""
    MAXSCALE_CHECK_INTERVAL_SECONDS: int = 30

    # MaxScale replication monitoring. Leave the URL empty to disable it.
    MAXSCALE_API_URL: str = ""
    MAXSCALE_API_USERNAME: str = ""
    MAXSCALE_API_PASSWORD: str = ""
    MAXSCALE_CHECK_INTERVAL_SECONDS: int = 30

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
