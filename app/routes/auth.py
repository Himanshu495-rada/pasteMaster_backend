"""Authentication routes: register, login, and current-user lookup."""
from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from ..extensions import db, limiter
from ..models import User

auth_bp = Blueprint("auth", __name__)


def _clean_email(raw: str):
    """Validate + normalize an email, or return None if invalid."""
    try:
        # check_deliverability=False keeps registration offline-friendly.
        return validate_email(raw, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return None


@auth_bp.post("/register")
@limiter.limit("10 per hour")
def register():
    data = request.get_json(silent=True) or {}
    email = _clean_email((data.get("email") or "").strip())
    password = data.get("password") or ""

    if not email:
        return jsonify(error="A valid email is required"), 400
    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters"), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with that email already exists"), 409

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify(access_token=token, user=user.to_dict()), 201


@auth_bp.post("/login")
@limiter.limit("20 per hour")
def login():
    data = request.get_json(silent=True) or {}
    email = _clean_email((data.get("email") or "").strip())
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first() if email else None
    if not user or not user.check_password(password):
        return jsonify(error="Invalid email or password"), 401

    token = create_access_token(identity=str(user.id))
    return jsonify(access_token=token, user=user.to_dict())


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found"), 404
    return jsonify(user=user.to_dict())
