from urllib.parse import urlsplit
from cryptography.fernet import Fernet
from sqlalchemy.engine import make_url


def validate_production(config):
    if not config["PRODUCTION"]:
        return
    errors = []
    if config.get("DEBUG") or config.get("TESTING"):
        errors.append("debug/testing deben estar desactivados")
    for key in ("JWT_SECRET_KEY", "MAIL_ENCRYPTION_KEY"):
        if not isinstance(config.get(key), str) or len(config[key].encode()) < 32:
            errors.append(f"falta un secreto seguro para {key}")
    try:
        Fernet(config.get("MAIL_ENCRYPTION_KEY", "").encode())
    except (ValueError, TypeError, AttributeError):
        errors.append("MAIL_ENCRYPTION_KEY debe ser una clave Fernet")
    try:
        if make_url(config.get("SQLALCHEMY_DATABASE_URI")).get_backend_name() != "postgresql":
            errors.append("producción requiere PostgreSQL")
    except Exception:
        errors.append("DATABASE_URL inválida")
    url = urlsplit(config["FRONTEND_URL"])
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.path not in ("", "/") or url.query or url.fragment:
        errors.append("FRONTEND_URL debe ser un origen HTTPS sin rutas ni credenciales")
    if not config.get("TRUSTED_HOSTS") or "*" in config["TRUSTED_HOSTS"]:
        errors.append("configurar TRUSTED_HOSTS explícitamente")
    if config["SMTP_TLS"] == config["SMTP_SSL"]:
        errors.append("activar exactamente uno de SMTP_TLS/SMTP_SSL")
    if config.get("REGISTRATION_CODE") and len(config["REGISTRATION_CODE"].encode()) < 32:
        errors.append("REGISTRATION_CODE debe tener al menos 32 bytes o quedar vacío para deshabilitar el registro")
    if not config["AUTH_RATE_LIMIT_ENABLED"]:
        errors.append("los límites de autenticación deben estar activos")
    if errors:
        raise RuntimeError("Configuración de producción inválida: " + "; ".join(errors))
