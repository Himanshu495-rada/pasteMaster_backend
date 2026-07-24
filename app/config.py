"""Application configuration, driven entirely by environment variables.

All secrets and connection strings come from the environment so the same code
runs locally (SQLite by default) and on PythonAnywhere (MySQL) without edits.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

# Load a local .env if present (no-op in production where vars are set in WSGI).
load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    # --- Core secrets -------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=_int("JWT_EXPIRES_DAYS", 7))

    # --- Database -----------------------------------------------------------
    # On PythonAnywhere use:
    #   mysql+pymysql://user:pass@user.mysql.pythonanywhere-services.com/user$dbname
    # Locally we fall back to a SQLite file so `python run.py` works with no setup.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///pastemaster.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # MySQL connections on shared hosts drop when idle; recycle before that.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280, "pool_pre_ping": True}

    # --- CORS ---------------------------------------------------------------
    # Comma-separated list of allowed origins. Defaults to common dev ports.
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]

    # --- Paste rules --------------------------------------------------------
    TEMP_PASTE_TTL_HOURS = _int("TEMP_PASTE_TTL_HOURS", 24)
    # Max serialized content size (bytes). Bounds pasted base64 images since
    # PythonAnywhere's free MySQL storage is limited. Default 3 MB.
    MAX_PASTE_BYTES = _int("MAX_PASTE_BYTES", 3 * 1024 * 1024)
    # Reject oversized request bodies at the WSGI layer (small headroom over the
    # content cap for JSON overhead).
    MAX_CONTENT_LENGTH = MAX_PASTE_BYTES + (256 * 1024)

    # --- Rate limiting ------------------------------------------------------
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per hour")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
