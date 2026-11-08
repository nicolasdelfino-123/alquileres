from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.models import User
from app.repositories.auth_repository import AuthRepository
from app.services.management_service import APIError, transactional

# Avoid revealing whether a username exists through an immediate password failure.
DUMMY_PASSWORD_HASH = generate_password_hash(uuid4().hex)


def jwt_secret():
    secret = current_app.config.get("JWT_SECRET_KEY")
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise APIError("Autenticación no configurada: se requiere JWT_SECRET_KEY de al menos 32 bytes", 503)
    return secret


class AuthService:
    @staticmethod
    def login(data):
        if not isinstance(data, dict) or set(data) != {"username", "password"}:
            raise APIError("Se requieren username y password")
        username, password = data["username"], data["password"]
        if not isinstance(username, str) or not isinstance(password, str) or not username.strip() or not password:
            raise APIError("Se requieren username y password")
        if len(username) > 100 or len(password) > 1024:
            raise APIError("Credenciales inválidas", 401)
        secret = jwt_secret()
        user = AuthRepository.by_username(username.strip())
        valid = check_password_hash(user.password_hash if user else DUMMY_PASSWORD_HASH, password)
        if not valid or user is None or not user.is_active or user.role not in {"admin", "operator"}:
            raise APIError("Credenciales inválidas", 401)
        now = datetime.now(timezone.utc)
        lifetime = current_app.config["JWT_ACCESS_TOKEN_MINUTES"]
        token = jwt.encode({"sub": str(user.id), "iat": now, "nbf": now,
                            "exp": now + timedelta(minutes=lifetime), "jti": uuid4().hex,
                            "iss": "alquileres-backend", "aud": "alquileres-api", "type": "access", "role": user.role, "version": user.auth_version},
                           secret, algorithm="HS256")
        return {"access_token": token, "token_type": "Bearer", "expires_in": lifetime * 60,
                "user": {"id": user.id, "username": user.username, "role": user.role}}

    @staticmethod
    def authenticate(token):
        try:
            claims = jwt.decode(token, jwt_secret(), algorithms=["HS256"],
                                issuer="alquileres-backend", audience="alquileres-api",
                                options={"require": ["sub", "exp", "iat", "nbf", "jti", "iss", "aud"]})
            if claims.get("type") != "access" or not claims["sub"].isdigit():
                raise jwt.InvalidTokenError()
            user = AuthRepository.by_id(int(claims["sub"]))
        except (jwt.InvalidTokenError, ValueError, TypeError):
            raise APIError("Token inválido o vencido", 401) from None
        if user is None or not user.is_active or user.role not in {"admin", "operator"} or claims.get("version") != user.auth_version:
            raise APIError("Usuario no autorizado", 401)
        return user

    @staticmethod
    @transactional
    def create_user(username, email, password, role):
        if role not in {"admin", "operator"}:
            raise APIError("Rol inválido")
        if not username or len(username.strip()) > 100 or not email or len(email.strip()) > 150 or "@" not in email:
            raise APIError("Usuario o email inválido")
        if len(password) < 12 or len(password) > 1024:
            raise APIError("La contraseña debe tener entre 12 y 1024 caracteres")
        user = User(username=username.strip(), email=email.strip(), role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        return user
