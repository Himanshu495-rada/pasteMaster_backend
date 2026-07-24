# PasteMaster — Backend (Flask API)

A small Flask + SQLAlchemy API powering PasteMaster, a "shareable clipboard
across devices". Anonymous pastes are one-time-read; registered users get
persistent, editable, reshareable pastes.

## Stack
Flask 3 · Flask-SQLAlchemy · Flask-JWT-Extended · Flask-Cors · Flask-Limiter ·
PyMySQL · bleach (HTML sanitization).

## Layout
```
backend/
├── app/
│   ├── __init__.py      # app factory
│   ├── config.py        # env-driven config
│   ├── extensions.py    # db, jwt, cors, limiter
│   ├── models.py        # User, Paste, TempPaste
│   ├── utils.py         # code gen, HTML sanitization, expiry purge
│   └── routes/          # auth.py, paste.py
├── wsgi.py              # PythonAnywhere entry (exports `application`)
├── run.py               # local dev entry (port 3000)
├── cleanup.py           # daily expired-temp-paste purge
├── requirements.txt
└── .env.example
```

## API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/auth/register` | — | `{email, password}` → `{access_token, user}` |
| POST | `/api/auth/login` | — | `{email, password}` → `{access_token, user}` |
| GET  | `/api/auth/me` | JWT | current user |
| POST | `/api/paste` | optional | create paste → `{code, owned, expires_at?}` |
| GET  | `/api/paste/:code` | — | retrieve (temp pastes deleted after this read) |
| GET  | `/api/paste` | JWT | list the current user's pastes |
| PUT  | `/api/paste/:code` | JWT owner | edit content/title |
| DELETE | `/api/paste/:code` | JWT owner | delete |
| POST | `/api/paste/:code/reshare` | JWT owner | rotate to a new code |

`Authorization: Bearer <token>` carries the JWT. Create/retrieve treat the JWT
as **optional** — with it you get an owned paste, without it an anonymous
one-time-read paste.

## Run locally
```bash
cd backend
python -m venv venv
venv\Scripts\activate           # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env          # then edit secrets (SQLite is used by default)
python run.py                   # serves http://127.0.0.1:3000
```
With no `DATABASE_URL` set, a local `pastemaster.db` SQLite file is created
automatically — no MySQL needed for development.

### Quick smoke test
```bash
# anonymous create
curl -s -X POST http://127.0.0.1:3000/api/paste \
  -H "Content-Type: application/json" \
  -d "{\"content_html\":\"<p>hello</p>\",\"content_type\":\"richtext\"}"
# -> {"code":"ABC234","owned":false,"expires_at":"..."}

# retrieve (works once)
curl -s http://127.0.0.1:3000/api/paste/ABC234
# retrieve again -> 404 (one-time read confirmed)
```

## Deploy to PythonAnywhere (free tier)

1. **Upload** the `backend/` folder to `/home/YOURUSER/Pastemaster/backend`
   (git clone, or the Files tab).
2. **Create a MySQL database** in the *Databases* tab (e.g. `pastemaster`).
   Note the host `YOURUSER.mysql.pythonanywhere-services.com` and your DB
   password.
3. **Virtualenv** (Bash console):
   ```bash
   cd ~/Pastemaster/backend
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Web tab → Add a new web app → Manual configuration** (matching Python
   version). Set the *Virtualenv* to `/home/YOURUSER/Pastemaster/backend/venv`.
5. **Edit the WSGI file** (Web tab link). Replace its contents with env vars +
   the app import:
   ```python
   import os, sys
   path = "/home/YOURUSER/Pastemaster/backend"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["SECRET_KEY"] = "..."         # long random string
   os.environ["JWT_SECRET_KEY"] = "..."     # long random string
   os.environ["DATABASE_URL"] = (
       "mysql+pymysql://YOURUSER:DBPASSWORD@"
       "YOURUSER.mysql.pythonanywhere-services.com/YOURUSER$pastemaster"
   )
   os.environ["CORS_ORIGINS"] = "https://your-frontend-domain"

   from wsgi import application
   ```
6. **Reload** the web app. Tables are created automatically on first boot
   (`db.create_all()`), and `/api/health` should return `{"status":"ok"}`.
7. **Scheduled task** (Tasks tab, daily):
   ```
   python3.10 /home/YOURUSER/Pastemaster/backend/cleanup.py
   ```

### Notes
- Keep `CORS_ORIGINS` set to your real frontend origin(s) in production — never
  `*`.
- Pasted images are stored inline as base64 (LONGTEXT); `MAX_PASTE_BYTES`
  (default 3 MB) bounds each paste to protect free-tier storage.
- All stored HTML is sanitized with a strict bleach allow-list on write.
