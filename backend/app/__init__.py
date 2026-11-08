from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlsplit
import os

from app.extensions import db, migrate

def create_app(config=None):
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_MINUTES"] = 30

    app.config.update(
        PRODUCTION=os.getenv("APP_ENV", "development") == "production",
        DEBUG=False,
        MAX_CONTENT_LENGTH=64 * 1024,
        AUTH_RATE_LIMIT_ENABLED=True,
        MAIL_ENCRYPTION_KEY=os.getenv("MAIL_ENCRYPTION_KEY"),
        SMTP_TIMEOUT=15,
        MAIL_MAX_ATTEMPTS=6,
        MAIL_WORKER_AUTOSTART=os.getenv("MAIL_WORKER_AUTOSTART", "true").lower() == "true",
        PROXY_HOPS=int(os.getenv("PROXY_HOPS", "0")),
        TRUSTED_HOSTS=[host.strip() for host in os.getenv("TRUSTED_HOSTS", "").split(",") if host.strip()] or None,
        REGISTRATION_CODE=os.getenv("REGISTRATION_CODE"),
        FRONTEND_URL=os.getenv("FRONTEND_URL", "http://localhost:5173"),
        SMTP_HOST=os.getenv("SMTP_HOST"),
        SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
        SMTP_USERNAME=os.getenv("SMTP_USERNAME"),
        SMTP_PASSWORD=os.getenv("SMTP_PASSWORD"),
        SMTP_FROM=os.getenv("SMTP_FROM"),
        SMTP_TLS=os.getenv("SMTP_TLS", "true").lower() == "true",
        SMTP_SSL=os.getenv("SMTP_SSL", "false").lower() == "true",
    )

    if config:
        app.config.update(config)

    if not app.config["PRODUCTION"] and not app.config.get("MAIL_ENCRYPTION_KEY"):
        from cryptography.fernet import Fernet
        key_path = Path(app.instance_path) / "mail.key"
        key_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(Fernet.generate_key())
        app.config["MAIL_ENCRYPTION_KEY"] = key_path.read_text().strip()

    from app.production import validate_production
    validate_production(app.config)
    origin = urlsplit(app.config["FRONTEND_URL"])
    CORS(app, resources={r"/api/*": {"origins": [f"{origin.scheme}://{origin.netloc}"]}},
         allow_headers=["Content-Type", "Authorization"], supports_credentials=False)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "hide_parameters": True}
    if app.config["PROXY_HOPS"]:
        from werkzeug.middleware.proxy_fix import ProxyFix
        hops = app.config["PROXY_HOPS"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops)

    @app.after_request
    def secure_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if app.config["PRODUCTION"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if response.status_code == 429:
            response.headers["Retry-After"] = "300"
        return response

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db.session.rollback()
            return {"status": "unavailable"}, 503
        return {"status": "ok"}

    db.init_app(app)
    migrate.init_app(app, db)

    # Importar todos los modelos para SQLAlchemy y Flask-Migrate.
    from app import models

    from app.routes.mail_settings_routes import mail_settings_bp
    app.register_blueprint(mail_settings_bp, url_prefix="/api")

    from app.routes.workbook_routes import workbook_bp
    app.register_blueprint(workbook_bp, url_prefix="/api")

    from app.routes.document_routes import file_bp, init_document_limits
    app.register_blueprint(file_bp, url_prefix="/api")
    init_document_limits(app)

    from app.routes.rental_workspace_routes import workspace_bp
    app.register_blueprint(workspace_bp, url_prefix="/api")

    # Importar rutas
    from app.routes.property_routes import property_bp
    app.register_blueprint(property_bp, url_prefix="/api")

    from app.routes.management_routes import management_bp
    app.register_blueprint(management_bp, url_prefix="/api")

    from app.services.management_service import APIError
    from sqlalchemy.exc import IntegrityError
    from werkzeug.exceptions import BadRequest, UnsupportedMediaType

    @app.errorhandler(APIError)
    def handle_api_error(error):
        db.session.rollback()
        return {"error": str(error)}, error.status

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        db.session.rollback()
        return {"error": "La operación viola una restricción de integridad"}, 409

    @app.errorhandler(BadRequest)
    @app.errorhandler(UnsupportedMediaType)
    def handle_bad_request(error):
        db.session.rollback()
        return {"error": "Solicitud JSON inválida"}, 400

    from werkzeug.exceptions import RequestEntityTooLarge

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(error):
        return {"error": "La solicitud supera el tamaño permitido"}, 413

    @app.errorhandler(500)
    def handle_server_error(error):
        db.session.rollback()
        return {"error": "No se pudo completar la operación. Intentá nuevamente."}, 500

    from app.routes.auth_routes import init_auth
    from app.services.rate_limit_service import limit_auth_requests
    app.before_request(limit_auth_requests)
    init_auth(app)
    from app.mail_cli import init_mail_cli
    init_mail_cli(app)

    from app.mail_runtime import init_mail_runtime
    init_mail_runtime(app)

    return app
