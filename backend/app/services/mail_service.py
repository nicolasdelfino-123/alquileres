"""Durable transactional outbox. Run multiple workers against PostgreSQL, not SQLite."""
import json
import smtplib
import ssl
from datetime import timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from urllib.parse import urlencode

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from sqlalchemy import select

from app.extensions import db
from app.models.auth_token_model import AuthToken
from app.models.mail_outbox_model import MailOutbox
from app.models.common import utcnow
from app.services.management_service import APIError


def cipher():
    key = current_app.config.get("MAIL_ENCRYPTION_KEY")
    if not key:
        raise APIError("Falta la clave de cifrado del correo en el servidor.", 503)
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError):
        raise APIError("MAIL_ENCRYPTION_KEY inválida", 503) from None


def smtp_config():
    from app.models.mail_settings_model import MailSettings
    config = dict(current_app.config)
    settings = db.session.get(MailSettings, 1)
    if settings:
        try:
            password = cipher().decrypt(settings.credentials.encode()).decode()
        except InvalidToken:
            raise APIError("No se pudo descifrar el correo configurado", 503) from None
        config.update(SMTP_HOST="smtp.gmail.com", SMTP_PORT=587, SMTP_FROM=settings.email,
                      SMTP_USERNAME=settings.email, SMTP_PASSWORD=password, SMTP_TLS=True, SMTP_SSL=False)
    return config


def validate_smtp():
    config = smtp_config()
    missing = [name for name in ("SMTP_HOST", "SMTP_FROM", "SMTP_USERNAME", "SMTP_PASSWORD") if not config.get(name)]
    if missing:
        raise APIError("El envío de correos todavía no está configurado. Contactá al administrador.", 503)
    if config["SMTP_TLS"] == config["SMTP_SSL"]:
        raise APIError("Configurá exactamente uno de SMTP_TLS o SMTP_SSL", 503)
    return config


def enqueue(user, purpose, raw_token, token):
    validate_smtp()
    encrypted = cipher().encrypt(json.dumps({"email": user.email, "purpose": purpose, "token": raw_token}).encode()).decode()
    db.session.add(MailOutbox(token_id=token.id, payload=encrypted))


def build_message(email, purpose, token, message_id=None):
    config = smtp_config()
    # Fragment is not sent in HTTP requests, access logs, or referrer headers.
    url = config["FRONTEND_URL"].rstrip("/") + "/cuenta?" + urlencode({"action": purpose}) + "#" + urlencode({"token": token})
    message = EmailMessage()
    message["From"] = config["SMTP_FROM"]
    message["To"] = email
    message["Date"] = format_datetime(utcnow().replace(tzinfo=timezone.utc))
    message["Message-ID"] = message_id or make_msgid()
    message["Subject"] = "Verificá tu correo · Bricks Bienes Raíces" if purpose == "verify" else "Restablecé tu contraseña · Bricks Bienes Raíces"
    message.set_content(f"Abrí este enlace para {'verificar tu correo' if purpose == 'verify' else 'elegir una nueva contraseña'}:\n\n{url}\n\nVence en {'24 horas' if purpose == 'verify' else '30 minutos'} desde la solicitud y se puede usar una sola vez. Si no lo solicitaste, ignorá este correo.")
    return message


def deliver(message):
    config = validate_smtp()
    context = ssl.create_default_context()
    kwargs = {"timeout": config["SMTP_TIMEOUT"]}
    if config["SMTP_SSL"]:
        kwargs["context"] = context
    transport = smtplib.SMTP_SSL if config["SMTP_SSL"] else smtplib.SMTP
    with transport(config["SMTP_HOST"], config["SMTP_PORT"], **kwargs) as smtp:
        if config["SMTP_TLS"]:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
        refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def process_one():
    """Lock one due item until SMTP finishes. Crash can redeliver the same link."""
    now = utcnow()
    item = db.session.scalar(select(MailOutbox).where(MailOutbox.status == "pending", MailOutbox.available_at <= now)
                             .order_by(MailOutbox.available_at, MailOutbox.id).with_for_update(skip_locked=True).limit(1))
    if item is None:
        db.session.rollback()
        return False
    token = db.session.get(AuthToken, item.token_id)
    if not token or token.used_at or token.expires_at <= now:
        item.status, item.payload, item.finished_at = "cancelled", None, now
        db.session.commit()
        return True
    item.attempts += 1
    try:
        payload = json.loads(cipher().decrypt(item.payload.encode()).decode())
        message_id = f"<pako-auth-{item.id}@{smtp_config()['SMTP_FROM'].split('@')[-1]}>"
        deliver(build_message(payload["email"], payload["purpose"], payload["token"], message_id))
    except (smtplib.SMTPException, OSError, InvalidToken, APIError, ValueError, KeyError) as error:
        item.last_error = type(error).__name__
        # Never log exception text: SMTP replies can contain recipient addresses.
        current_app.logger.warning("mail_delivery_failed id=%s attempt=%s error=%s", item.id, item.attempts, item.last_error)
        permanent = isinstance(error, (smtplib.SMTPRecipientsRefused, InvalidToken)) or (
            isinstance(error, smtplib.SMTPResponseException) and 500 <= error.smtp_code < 600
            and not isinstance(error, smtplib.SMTPAuthenticationError))
        delay = min(60 * 2 ** (item.attempts - 1), 900)
        if permanent or item.attempts >= current_app.config["MAIL_MAX_ATTEMPTS"] or now + timedelta(seconds=delay) >= token.expires_at:
            item.status, item.payload, item.finished_at = "failed", None, now
        else:
            item.available_at = now + timedelta(seconds=delay)
    else:
        item.status, item.payload, item.finished_at, item.last_error = "sent", None, now, None
    db.session.commit()
    return True
