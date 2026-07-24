"""Paste routes: create, retrieve, list, update, delete, reshare.

Anonymous creates land in ``TempPaste`` (one-time read + TTL); authenticated
creates land in ``Paste`` (persistent, owned by the user).
"""
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db, limiter
from ..models import Paste, TempPaste, User
from ..utils import generate_code, purge_expired, sanitize_html

paste_bp = Blueprint("paste", __name__)

VALID_TYPES = {"richtext", "code", "image", "mixed", "text"}


def _validate_content(data: dict):
    """Return (content_html, content_type, error_response)."""
    content = data.get("content_html")
    if not content or not content.strip():
        return None, None, (jsonify(error="Content cannot be empty"), 400)

    max_bytes = current_app.config["MAX_PASTE_BYTES"]
    if len(content.encode("utf-8")) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        return None, None, (jsonify(error=f"Content exceeds the {mb} MB limit"), 413)

    content_type = data.get("content_type", "richtext")
    if content_type not in VALID_TYPES:
        content_type = "richtext"

    return sanitize_html(content), content_type, None


@paste_bp.post("")
@limiter.limit("60 per hour")
@jwt_required(optional=True)
def create_paste():
    data = request.get_json(silent=True) or {}
    content_html, content_type, err = _validate_content(data)
    if err:
        return err

    # Opportunistic cleanup keeps the temp table small without a cron guarantee.
    purge_expired()

    user_id = get_jwt_identity()
    code = generate_code()

    if user_id:
        title = (data.get("title") or "").strip()[:200] or None
        paste = Paste(
            code=code,
            user_id=int(user_id),
            title=title,
            content_html=content_html,
            content_type=content_type,
        )
        db.session.add(paste)
        db.session.commit()
        return jsonify(code=code, owned=True), 201

    ttl = current_app.config["TEMP_PASTE_TTL_HOURS"]
    temp = TempPaste(
        code=code,
        content_html=content_html,
        content_type=content_type,
        expires_at=datetime.utcnow() + timedelta(hours=ttl),
    )
    db.session.add(temp)
    db.session.commit()
    return (
        jsonify(code=code, owned=False, expires_at=temp.expires_at.isoformat() + "Z"),
        201,
    )


@paste_bp.get("/<code>")
def retrieve_paste(code):
    code = (code or "").strip().upper()

    # Persistent pastes: return and keep (increment views).
    paste = Paste.query.filter_by(code=code).first()
    if paste:
        paste.view_count += 1
        db.session.commit()
        return jsonify(paste.to_dict(include_content=True))

    # Temp pastes: enforce expiry, then one-time read (return, then delete).
    temp = TempPaste.query.filter_by(code=code).first()
    if temp:
        if temp.expires_at < datetime.utcnow():
            db.session.delete(temp)
            db.session.commit()
            return jsonify(error="This paste has expired"), 404
        payload = temp.to_dict()
        db.session.delete(temp)
        db.session.commit()
        return jsonify(payload)

    return jsonify(error="No paste found for that code"), 404


@paste_bp.get("")
@jwt_required()
def list_pastes():
    user_id = int(get_jwt_identity())
    pastes = (
        Paste.query.filter_by(user_id=user_id)
        .order_by(Paste.updated_at.desc())
        .all()
    )
    return jsonify(pastes=[p.to_dict(include_content=False) for p in pastes])


def _owned_paste_or_error(code, user_id):
    paste = Paste.query.filter_by(code=code.strip().upper()).first()
    if not paste:
        return None, (jsonify(error="Paste not found"), 404)
    if paste.user_id != user_id:
        return None, (jsonify(error="You do not own this paste"), 403)
    return paste, None


@paste_bp.put("/<code>")
@jwt_required()
def update_paste(code):
    user_id = int(get_jwt_identity())
    paste, err = _owned_paste_or_error(code, user_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if "content_html" in data:
        content_html, content_type, verr = _validate_content(data)
        if verr:
            return verr
        paste.content_html = content_html
        paste.content_type = content_type
    if "title" in data:
        paste.title = (data.get("title") or "").strip()[:200] or None

    db.session.commit()
    return jsonify(paste.to_dict(include_content=True))


@paste_bp.delete("/<code>")
@jwt_required()
def delete_paste(code):
    user_id = int(get_jwt_identity())
    paste, err = _owned_paste_or_error(code, user_id)
    if err:
        return err
    db.session.delete(paste)
    db.session.commit()
    return jsonify(status="deleted", code=paste.code)


@paste_bp.post("/<code>/reshare")
@jwt_required()
def reshare_paste(code):
    """Rotate to a fresh share code; the old link stops working."""
    user_id = int(get_jwt_identity())
    paste, err = _owned_paste_or_error(code, user_id)
    if err:
        return err
    paste.code = generate_code()
    db.session.commit()
    return jsonify(code=paste.code)
