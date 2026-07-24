"""WSGI entry point for PythonAnywhere.

In the PythonAnywhere "Web" tab, edit the WSGI configuration file so it adds
this project directory to sys.path and imports ``application`` from here, e.g.:

    import sys
    path = "/home/YOURUSER/Pastemaster/backend"
    if path not in sys.path:
        sys.path.insert(0, path)
    from wsgi import application

Environment variables (SECRET_KEY, JWT_SECRET_KEY, DATABASE_URL, CORS_ORIGINS)
can be set at the top of that same WSGI file via os.environ before this import,
or loaded from a .env file placed next to this module.
"""
from app import create_app

application = create_app()
