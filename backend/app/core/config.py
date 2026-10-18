import json
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Resolve repository root and backend directory paths
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(BACKEND_DIR.parent / ".env", override=False)

# Application Identity & Storage
APP_NAME: str = os.getenv("APP_NAME", "VeriSphere")
APP_ENV: str = os.getenv("APP_ENV", "development").lower()
UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", str(BACKEND_DIR / "uploads"))).resolve()

# Server Runtime
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8088"))
DEBUG: bool = os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
WORKERS_COUNT: int = int(os.getenv("WORKERS_COUNT", "1"))

# Database & Cache
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://tushar:password@localhost:5432/verisphere"
)
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Security & Tokens
SECRET_KEY: str = os.getenv("SECRET_KEY", "development-only-change-this-verisphere-key")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Initial Admin Bootstrap
INITIAL_ADMIN_EMAIL: str = os.getenv("INITIAL_ADMIN_EMAIL", "")
INITIAL_ADMIN_PASSWORD: str = os.getenv("INITIAL_ADMIN_PASSWORD", "")

# AI Engine Configurations
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# SMTP / Email Logic
MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM: str = os.getenv("MAIL_FROM")
MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "VeriSphere Official")
MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtpout.secureserver.net")
MAIL_PORT: int = int(os.getenv("MAIL_PORT", "465"))
MAIL_USE_TLS: bool = os.getenv("MAIL_USE_TLS", "false").strip().lower() in {"1", "true", "yes", "on"}
MAIL_USE_SSL: bool = os.getenv("MAIL_USE_SSL", "true").strip().lower() in {"1", "true", "yes", "on"}

# LinkedIn OpenID Connect (optional)
LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
LINKEDIN_REDIRECT_URI: str = os.getenv("LINKEDIN_REDIRECT_URI", "")
LINKEDIN_SCOPES: str = os.getenv("LINKEDIN_SCOPES", "openid profile")

# Student invitation links
FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "http://localhost:5176").rstrip("/")
STUDENT_INVITATION_EXPIRE_HOURS: int = int(
    os.getenv("STUDENT_INVITATION_EXPIRE_HOURS", "24")
)

# Robust CORS Origins Parser (Handles JSON list or comma-separated strings)
raw_origins = os.getenv("BACKEND_CORS_ORIGINS") or os.getenv("FRONTEND_ORIGINS")
FRONTEND_ORIGINS: List[str] = []

if raw_origins:
    raw_origins = raw_origins.strip()
    if raw_origins.startswith("[") and raw_origins.endswith("]"):
        try:
            parsed = json.loads(raw_origins)
            if isinstance(parsed, list):
                FRONTEND_ORIGINS = [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            FRONTEND_ORIGINS = [item.strip() for item in raw_origins.strip("[]").split(",") if item.strip()]
    else:
        FRONTEND_ORIGINS = [item.strip() for item in raw_origins.split(",") if item.strip()]
else:
    FRONTEND_ORIGINS = [
        "https://verisphere.hacksmiths.dev",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ]

# System Invariant Validation
if APP_ENV == "production" and (
    SECRET_KEY == "development-only-change-this-verisphere-key"
    or SECRET_KEY.startswith("replace-")
    or len(SECRET_KEY) < 32
):
    raise RuntimeError(
        "CRITICAL: Set SECRET_KEY to a random value of at least 32 characters "
        "before starting in production."
    )

if not 1 <= PORT <= 65535:
    raise ValueError(f"PORT must be between 1 and 65535. Received: {PORT}")

if WORKERS_COUNT < 1:
    raise ValueError(f"WORKERS_COUNT must be >= 1. Received: {WORKERS_COUNT}")

if STUDENT_INVITATION_EXPIRE_HOURS < 1:
    raise ValueError("STUDENT_INVITATION_EXPIRE_HOURS must be at least 1.")

if APP_ENV == "production" and "*" in FRONTEND_ORIGINS:
    raise RuntimeError("Do not use wildcard CORS origins in production.")