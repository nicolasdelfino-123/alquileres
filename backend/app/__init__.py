from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

from app.extensions import db, migrate

def create_app(config=None):
    load_dotenv()

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_MINUTES"] = 30

    if config:
        app.config.update(config)

    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)

    # Importar todos los modelos para SQLAlchemy y Flask-Migrate.
    from app import models

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

    from app.routes.auth_routes import init_auth
    init_auth(app)

    return app
