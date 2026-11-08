"""Shared fixed-window limits, atomically enforced in the primary database."""
import hashlib
import hmac
import time
from datetime import datetime, timezone
from flask import current_app, request
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.extensions import db
from app.models.mail_outbox_model import AuthRateBucket
from app.services.management_service import APIError


def consume(scope, identity, limit, seconds):
    window = int(time.time()) // seconds
    raw = f"{scope}:{identity}:{window}".encode()
    secret = (current_app.config.get("JWT_SECRET_KEY") or "development-only").encode()
    key = hmac.new(secret, raw, hashlib.sha256).hexdigest()
    insert = pg_insert if db.engine.dialect.name == "postgresql" else sqlite_insert
    statement = insert(AuthRateBucket).values(key=key, count=1,
        expires_at=datetime.fromtimestamp((window + 1) * seconds, timezone.utc).replace(tzinfo=None))
    statement = statement.on_conflict_do_update(index_elements=[AuthRateBucket.key],
        set_={"count": AuthRateBucket.count + 1}).returning(AuthRateBucket.count)
    count = db.session.execute(statement).scalar_one()
    # Commit separately so rejected logins/validation failures still consume their budget.
    db.session.commit()
    if count > limit:
        raise APIError("Demasiados intentos. Esperá unos minutos y volvé a intentar.", 429)


def limit_auth_requests():
    if not current_app.config["AUTH_RATE_LIMIT_ENABLED"] or request.method != "POST":
        return
    if request.path.startswith('/api/settings/mail'):
        consume("mail-settings-ip", request.remote_addr or "unknown", 10, 300)
        return
    action = request.path.rstrip('/').rsplit('/', 1)[-1]
    if action not in {"login", "register", "forgot-password", "resend-verification", "verify-email", "reset-password"} or not request.path.startswith('/api/auth/'):
        return
    consume("auth-ip", request.remote_addr or "unknown", 60, 60)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return
    if action == "login":
        identity = data.get("username")
        if isinstance(identity, str):
            consume("login-user", identity.strip().casefold()[:100], 20, 300)
    elif action in {"register", "forgot-password", "resend-verification"}:
        consume("email-ip", request.remote_addr or "unknown", 10, 300)
        identity = data.get("email")
        if isinstance(identity, str):
            consume("email-user", identity.strip().lower()[:150], 5, 3600)
