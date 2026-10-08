from flask import g, jsonify
from app.controllers.management_controller import json_body
from app.services.auth_service import AuthService


class AuthController:
    @staticmethod
    def login():
        return jsonify(AuthService.login(json_body()))

    @staticmethod
    def me():
        user = g.current_user
        return jsonify({"id": user.id, "username": user.username, "email": user.email, "role": user.role})
