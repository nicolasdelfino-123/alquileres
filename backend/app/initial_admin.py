"""Initial local administrator. Existing accounts are never reset at startup."""
from sqlalchemy import select, or_
from app.extensions import db
from app.models import User

INITIAL_EMAIL = "nicolasdelfino585@gmail.com"
INITIAL_PASSWORD_HASH = 'scrypt:32768:8:1$8V35bYxvr0KWl9vS$4194e15e35080be1d2b03d8954bb389cb4d2d86acf37fab3f1411afc4d20bcb52b4913a1b8d13e21e0e47bc76a0409b176f09d5f9ef5c695c5f202da72a99d00'


def ensure_local_admin():
    existing = db.session.scalar(select(User).where(or_(User.username == "pako", User.email == INITIAL_EMAIL)))
    if existing:
        return existing
    user = User(username="pako", email=INITIAL_EMAIL, password_hash=INITIAL_PASSWORD_HASH,
                role="admin", is_active=True, email_pending=False)
    db.session.add(user)
    db.session.commit()
    return user
