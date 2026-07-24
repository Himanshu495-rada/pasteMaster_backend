"""Purge expired anonymous pastes.

Wire this up as a PythonAnywhere "Scheduled task" (free tier allows one daily):

    python3.10 /home/YOURUSER/Pastemaster/backend/cleanup.py

Retrieval already expires temp pastes lazily, so this only reclaims storage for
pastes that were created but never retrieved before their TTL elapsed.
"""
from app import create_app
from app.utils import purge_expired

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        removed = purge_expired()
        print(f"[cleanup] removed {removed} expired temp paste(s)")
