import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

APP_NAME = os.getenv("APP_NAME", "VeriSphere")
APP_ENV = os.getenv("APP_ENV", "development").lower()
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8088"))
DEBUG = os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
WORKERS_COUNT = int(os.getenv("WORKERS_COUNT", "1"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./verisphere.db")
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-this-verisphere-key")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "")
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_frontend_origins = os.getenv("FRONTEND_ORIGINS")
if _frontend_origins is None:
    _frontend_origins = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:5176,http://127.0.0.1:5176",
    )
    if _frontend_origins.lstrip().startswith("["):
        parsed_origins = json.loads(_frontend_origins)
        if not isinstance(parsed_origins, list) or not all(
            isinstance(origin, str) for origin in parsed_origins
        ):
            raise ValueError("BACKEND_CORS_ORIGINS must be a list of origin strings.")
        FRONTEND_ORIGINS = [
            origin.strip() for origin in parsed_origins if origin.strip()
        ]
    else:
        FRONTEND_ORIGINS = [
            origin.strip() for origin in _frontend_origins.split(",") if origin.strip()
        ]
else:
    FRONTEND_ORIGINS = [
        origin.strip() for origin in _frontend_origins.split(",") if origin.strip()
    ]

if APP_ENV == "production" and SECRET_KEY == "development-only-change-this-verisphere-key":
    raise RuntimeError("Set SECRET_KEY to a strong, unique value in production.")
if not 1 <= PORT <= 65535:
    raise ValueError("PORT must be between 1 and 65535.")
if WORKERS_COUNT < 1:
    raise ValueError("WORKERS_COUNT must be at least 1.")