"""Local development entry point:  python run.py

Uses the SQLite fallback in config unless DATABASE_URL is set in your .env.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)
