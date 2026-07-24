"""Database models: User, Paste (persistent, owned) and TempPaste (anonymous).

``content_html`` uses MySQL LONGTEXT (up to 4 GB) so pasted base64 images fit,
while degrading to plain TEXT on SQLite for frictionless local development.
"""
from datetime import datetime

from sqlalchemy.dialects.mysql import LONGTEXT
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

# LONGTEXT on MySQL, TEXT everywhere else (e.g. local SQLite).
LongText = db.Text().with_variant(LONGTEXT, "mysql")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    pastes = db.relationship(
        "Paste", backref="owner", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat() + "Z",
        }


class Paste(db.Model):
    """Persistent paste owned by a registered user. Survives retrieval."""

    __tablename__ = "pastes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False, index=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    title = db.Column(db.String(200), nullable=True)
    content_html = db.Column(LongText, nullable=False)
    content_type = db.Column(db.String(20), nullable=False, default="richtext")
    view_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self, include_content: bool = True) -> dict:
        data = {
            "code": self.code,
            "title": self.title,
            "content_type": self.content_type,
            "view_count": self.view_count,
            "owned": True,
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z",
        }
        if include_content:
            data["content_html"] = self.content_html
        else:
            # Lightweight snippet for list views (strip tags crudely).
            text = _strip_tags(self.content_html)
            data["preview"] = text[:160]
        return data


class TempPaste(db.Model):
    """Anonymous paste. One-time read: deleted on first successful retrieval,
    and expires after a TTL if never retrieved."""

    __tablename__ = "temp_pastes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False, index=True)
    content_html = db.Column(LongText, nullable=False)
    content_type = db.Column(db.String(20), nullable=False, default="richtext")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": None,
            "content_html": self.content_html,
            "content_type": self.content_type,
            "owned": False,
            "created_at": self.created_at.isoformat() + "Z",
        }


def _strip_tags(html: str) -> str:
    """Very small tag stripper for list previews (not for security)."""
    import re

    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()
