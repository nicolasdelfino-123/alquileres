import re
import secrets
import smtplib
from email.message import EmailMessage
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, request
from sqlalchemy import select
from cryptography.fernet import InvalidToken
from app.extensions import db
from app.models import User
from app.models.mail_settings_model import MailSettings
from app.services.mail_service import cipher, deliver
from app.services.management_service import APIError
from app.controllers.management_controller import json_body

mail_settings_bp = Blueprint("mail_settings", __name__)


def local_setup_allowed():
    # Never trust forwarded headers for bootstrap. Production always needs an admin.
    return (not current_app.config["PRODUCTION"] and not current_app.config["PROXY_HOPS"]
            and request.remote_addr in {"127.0.0.1", "::1"}
            and urlsplit(request.host_url).hostname in {"localhost", "127.0.0.1", "::1"})


def authorize():
    if not getattr(g, "current_user", None) or g.current_user.role != "admin":
        raise APIError("La configuración de correo requiere un administrador", 403)
    if request.method != "GET" and request.headers.get("Origin") != current_app.config["FRONTEND_URL"].rstrip('/'):
        raise APIError("Origen no autorizado", 403)


@mail_settings_bp.get("/settings/mail")
def read():
    authorize()
    settings = db.session.get(MailSettings, 1)
    configured = bool(settings) or bool(current_app.config.get("SMTP_USERNAME") and current_app.config.get("SMTP_PASSWORD"))
    code = current_app.config.get("REGISTRATION_CODE") or ""
    if settings and settings.registration_code:
        code = cipher().decrypt(settings.registration_code.encode()).decode()
    return {"configured": configured, "email": settings.email if settings else current_app.config.get("SMTP_USERNAME") or "",
            "registration_code": code, "can_create_admin": local_setup_allowed() and db.session.scalar(select(User.id).limit(1)) is None}


@mail_settings_bp.post("/settings/mail")
def save():
    authorize()
    data = json_body()
    if not isinstance(data, dict):
        raise APIError("Solicitud inválida")
    email, password = data.get("email"), data.get("password")
    code = data.get("registration_code")
    if not isinstance(email, str) or len(email.strip()) > 150 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
        raise APIError("Ingresá un correo válido")
    email = email.strip().lower()
    settings = db.session.get(MailSettings, 1, with_for_update=True)
    if password == "" and settings and settings.email == email:
        encrypted = settings.credentials
    else:
        if not isinstance(password, str) or len(''.join(password.split())) != 16:
            raise APIError("Ingresá la contraseña de aplicación del correo remitente (16 caracteres). La contraseña del usuario del sistema no va acá.")
        encrypted = cipher().encrypt(''.join(password.split()).encode()).decode()
    if code is not None and (not isinstance(code, str) or len(code.encode()) < 12 or len(code) > 200):
        raise APIError("El código de registro debe tener entre 12 y 200 caracteres")
    if not settings:
        settings = MailSettings(id=1, email=email, credentials=encrypted)
        db.session.add(settings)
    settings.email, settings.credentials = email, encrypted
    if code:
        settings.registration_code = cipher().encrypt(code.encode()).decode()
    elif not settings.registration_code and not current_app.config.get("REGISTRATION_CODE"):
        settings.registration_code = cipher().encrypt(secrets.token_urlsafe(24).encode()).decode()
    username, admin_password = data.get("username"), data.get("admin_password")
    if username or admin_password:
        if not local_setup_allowed() or db.session.scalar(select(User.id).limit(1)) is not None:
            raise APIError("Ya existe una cuenta. Ingresá con tu usuario.", 409)
        if not isinstance(username, str) or not username.strip() or len(username.strip()) > 100:
            raise APIError("Ingresá un nombre de usuario válido")
        if not isinstance(admin_password, str) or not 12 <= len(admin_password) <= 1024:
            raise APIError("La contraseña del administrador debe tener al menos 12 caracteres")
        user = User(username=username.strip(), email=email, role="admin", is_active=True)
        user.set_password(admin_password)
        db.session.add(user)
    db.session.commit()
    return {"message": "Configuración guardada.", "configured": True}


@mail_settings_bp.post("/settings/mail/test")
def test_mail():
    authorize()
    from app.services.mail_service import smtp_config
    config = smtp_config()
    message = EmailMessage()
    message['From'] = config['SMTP_FROM']
    message['To'] = config['SMTP_FROM']
    message['Subject'] = 'Prueba de correo · Bricks Bienes Raíces'
    message.set_content('El correo de Bricks Bienes Raíces está configurado. Ya podés enviar enlaces de recuperación de contraseña y verificación de cuentas.')
    try:
        deliver(message)
    except smtplib.SMTPAuthenticationError:
        raise APIError("Gmail rechazó el acceso del remitente. Revisá la contraseña de aplicación configurada.", 502) from None
    except (smtplib.SMTPException, OSError):
        raise APIError("No se pudo conectar con Gmail. Revisá la conexión y volvé a intentar.", 502) from None
    return {"message": "Gmail aceptó el correo de prueba. Revisá tu bandeja de entrada y spam."}
