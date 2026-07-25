"""Helpers: share-code generation, HTML sanitization, and expiry cleanup."""
import secrets
from datetime import datetime

import bleach

from .extensions import db
from .models import Paste, TempPaste

# Unambiguous charset: no 0/O, 1/I/L - easy to read aloud and type.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6

# --- HTML sanitization allow-list ------------------------------------------
ALLOWED_TAGS = [
    "p", "br", "span", "div",
    "strong", "b", "em", "i", "u", "s", "strike",
    "h1", "h2", "h3", "h4",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "a", "hr", "img",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "code": ["class"],   # language-xxx from the code-block highlighter
    "pre": ["class"],
    "span": ["class"],
    "*": ["class"],
}
# Permit data: URIs so clipboard-pasted (base64) images survive, plus https.
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "data"]


def generate_code() -> str:
    """Generate a share code that is unique across both paste tables."""
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET)
                       for _ in range(CODE_LENGTH))
        exists = (
            db.session.query(Paste.id).filter_by(code=code).first()
            or db.session.query(TempPaste.id).filter_by(code=code).first()
        )
        if not exists:
            return code
    raise RuntimeError(
        "Could not generate a unique code; namespace may be exhausted.")


def sanitize_html(html: str) -> str:
    """Strip anything not on the allow-list to prevent stored XSS.

    ``strip=True`` drops disallowed tags but keeps their text content.
    """
    cleaned = bleach.clean(
        html or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned


def purge_expired() -> int:
    """Delete temp pastes past their TTL. Returns the number removed."""
    deleted = (
        db.session.query(TempPaste)
        .filter(TempPaste.expires_at < datetime.utcnow())
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return deleted
