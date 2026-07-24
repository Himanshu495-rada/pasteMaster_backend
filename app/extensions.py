"""Shared extension singletons, initialized in the app factory.

Kept in their own module so models and routes can import them without creating
circular imports with the application factory in ``app/__init__.py``.
"""
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
