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
    # Default: a SQLite file stored next to the app. This works out of the box
    # on PythonAnywhere's free tier (no MySQL required) and for local dev.
    # To use MySQL instead, set DATABASE_URL, e.g.
    #   mysql+pymysql://user:pass@user.mysql.pythonanywhere-services.com/user$dbname
    # The absolute path ensures the web app and the cleanup task share one file
    # regardless of the current working directory.
    _BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    _DEFAULT_SQLITE = "sqlite:///" + os.path.join(_BASE_DIR, "pastemaster.db")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _DEFAULT_SQLITE)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        # SQLite connections are tied to the thread that created them; allow the
        # WSGI server's worker threads to share the pool safely.
        SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}
    else:
        # MySQL connections on shared hosts drop when idle; recycle before that.
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280, "pool_pre_ping": True}

    # --- CORS ---------------------------------------------------------------
    # Comma-separated list of allowed origins. Defaults to common dev ports.
    # A browser's Origin header never has a trailing slash, and Flask-Cors
    # matches exactly, so we strip any trailing slash to avoid a silent mismatch.
    CORS_ORIGINS = [
        o.strip().rstrip("/")
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

    # --- Deploy webhook (CI/CD) --------------------------------------------
    # Enables POST /api/deploy, which git-pulls and reloads the app. Disabled
    # unless DEPLOY_TOKEN is set. The caller (Jenkins) must send that token in
    # the X-Deploy-Token header. See README for the pipeline setup.
    DEPLOY_TOKEN = os.environ.get("DEPLOY_TOKEN")
    # Git working tree to pull in. Defaults to the repo root (this project).
    DEPLOY_REPO_DIR = os.environ.get("DEPLOY_REPO_DIR", _BASE_DIR)
    # The WSGI file to `touch` to trigger a PythonAnywhere reload after pulling.
    # e.g. /var/www/htsingh200_pythonanywhere_com_wsgi.py
    WSGI_FILE = os.environ.get("WSGI_FILE")
    # PythonAnywhere free tier reaches the internet through an HTTP proxy; git
    # needs it set. On paid accounts / other hosts, leave this unset.
    #   PA_PROXY=http://proxy.server:3128
    PA_PROXY = os.environ.get("PA_PROXY")
