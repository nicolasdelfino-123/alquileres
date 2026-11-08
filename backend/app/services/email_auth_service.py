import hashlib
import re
import secrets
from datetime import timedelta
from app.models.common import utcnow

from flask import current_app
from sqlalchemy import select, update, func
from app.extensions import db
from app.models import User
from app.models.auth_token_model import AuthToken
from app.services.management_service import APIError, transactional
from app.services.mail_service import enqueue

GENERIC = {"message": "Si el correo corresponde a una cuenta pendiente o habilitada, recibirás un enlace. Revisá también spam."}


def issue(user, purpose):
    # Serialize issuance and consumption on the user across web workers.
    db.session.execute(select(User.id).where(User.id == user.id).with_for_update()).scalar_one()
    now = utcnow()
    latest = db.session.scalar(select(AuthToken).where(AuthToken.user_id == user.id).order_by(AuthToken.created_at.desc()))
    if latest and latest.created_at > now - timedelta(seconds=60):
        return
    db.session.execute(update(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose, AuthToken.used_at.is_(None)).values(used_at=now))
    token = secrets.token_urlsafe(32)
    record = AuthToken(user_id=user.id, digest=hashlib.sha256(token.encode()).hexdigest(), purpose=purpose,
                       expires_at=now + (timedelta(hours=24) if purpose == "verify" else timedelta(minutes=30)))
    db.session.add(record)
    db.session.flush()
    enqueue(user, purpose, token, record)


class EmailAuthService:
    @staticmethod
    @transactional
    def handle(action, data):
        if not isinstance(data, dict):
            raise APIError("Solicitud inválida")
        if action in {"verify-email", "reset-password"}:
            raw = data.get("token")
            if not isinstance(raw, str) or not 20 <= len(raw) <= 200:
                raise APIError("El enlace es inválido o venció. Solicitá uno nuevo.")
            purpose = "verify" if action == "verify-email" else "reset"
            now = utcnow()
            token = db.session.scalar(select(AuthToken).where(AuthToken.digest == hashlib.sha256(raw.encode()).hexdigest(), AuthToken.purpose == purpose))
            if not token or token.used_at or token.expires_at <= now:
                raise APIError("El enlace es inválido o venció. Solicitá uno nuevo.")
            user = db.session.get(User, token.user_id, with_for_update=True, populate_existing=True)
            # Re-read after acquiring the common user lock (another request may have consumed it).
            db.session.refresh(token)
            if token.used_at or token.expires_at <= utcnow():
                raise APIError("El enlace es inválido o venció. Solicitá uno nuevo.")
            if purpose == "reset":
                password = data.get("password")
                if not isinstance(password, str) or not 12 <= len(password) <= 1024 or not password.strip():
                    raise APIError("La contraseña debe tener entre 12 y 1024 caracteres")
                if not user.is_active:
                    raise APIError("La cuenta no está habilitada", 403)
                user.set_password(password)
                user.auth_version += 1
            else:
                if not user.email_pending:
                    raise APIError("La cuenta no tiene una verificación pendiente", 400)
                user.email_pending = False
                user.is_active = True
            db.session.execute(update(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose, AuthToken.used_at.is_(None)).values(used_at=now))
            return {"message": "Correo verificado. Ya podés ingresar." if purpose == "verify" else "Contraseña actualizada. Ingresá con tu nueva contraseña."}

        email = data.get("email")
        if not isinstance(email, str) or len(email.strip()) > 150 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
            raise APIError("Ingresá un correo válido")
        email = email.strip().lower()
        user = db.session.scalar(select(User).where(func.lower(User.email) == email))
        if action == "register":
            username, password = data.get("username"), data.get("password")
            if not isinstance(username, str) or not username.strip() or len(username.strip()) > 100:
                raise APIError("Ingresá un usuario de hasta 100 caracteres")
            if not isinstance(password, str) or not 12 <= len(password) <= 1024 or not password.strip():
                raise APIError("La contraseña debe tener entre 12 y 1024 caracteres")
            if user:
                raise APIError("Ese correo ya tiene una cuenta. Iniciá sesión o recuperá tu contraseña.", 409)
            if db.session.scalar(select(User.id).where(User.username == username.strip())):
                raise APIError("Ese nombre de usuario no está disponible", 409)
            user = User(username=username.strip(), email=email, role="operator", is_active=True, email_pending=False)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            return {"message": "Cuenta creada. Ya podés iniciar sesión."}
        elif action == "resend-verification":
            if user and user.email_pending:
                issue(user, "verify")
        elif action == "forgot-password":
            if user and user.is_active:
                issue(user, "reset")
        return GENERIC
