from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

from app.extensions import db, migrate

def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)

    # Importar modelos
    from app.models.property_model import Property

    # Importar rutas
    from app.routes.property_routes import property_bp
    app.register_blueprint(property_bp, url_prefix="/api")

    return app