from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import validates
from app.extensions import db
from app.models.common import utcnow


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (db.CheckConstraint("role IN ('admin', 'operator', 'viewer')", name="ck_user_role"),)
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="operator")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    email_pending = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    auth_version = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    @validates("password_hash")
    def validate_password_hash(self, key, value):
        if not isinstance(value, str) or not value.startswith(("scrypt:", "pbkdf2:sha256:")) or value.count("$") != 2:
            raise ValueError("Utilice set_password para almacenar una contraseña segura")
        return value

    def set_password(self, password):
        if not isinstance(password, str) or not password.strip():
            raise ValueError("La contraseña es obligatoria")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
