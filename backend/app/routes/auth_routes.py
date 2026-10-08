import click
from flask import Blueprint, g, request

from app.controllers.auth_controller import AuthController
from app.services.auth_service import AuthService
from app.services.management_service import APIError


auth_bp = Blueprint("auth", __name__)
auth_bp.add_url_rule("/auth/login", "login", AuthController.login, methods=["POST"])
auth_bp.add_url_rule("/auth/me", "me", AuthController.me, methods=["GET"])


def init_auth(app):
    app.register_blueprint(auth_bp, url_prefix="/api")

    @app.before_request
    def protect_api():
        if not request.path.startswith("/api/") or request.method == "OPTIONS" or request.endpoint == "auth.login":
            return None
        authorization = request.headers.get("Authorization", "").split()
        if len(authorization) != 2 or authorization[0].lower() != "bearer":
            raise APIError("Se requiere Authorization: Bearer <token>", 401)
        user = AuthService.authenticate(authorization[1])
        g.current_user = user
        admin_required = request.method == "DELETE" or request.path.rstrip("/").endswith("/cancel")
        if admin_required and user.role != "admin":
            raise APIError("Esta operación requiere rol admin", 403)

    @app.cli.command("create-user")
    @click.option("--username", required=True)
    @click.option("--email", required=True)
    @click.option("--role", type=click.Choice(["admin", "operator"]), default="operator")
    @click.password_option()
    def create_user(username, email, role, password):
        """Create an internal user without a public registration endpoint."""
        try:
            user = AuthService.create_user(username, email, password, role)
        except APIError as error:
            raise click.ClickException(str(error)) from None
        click.echo(f"Usuario {user.username} creado ({user.role})")
