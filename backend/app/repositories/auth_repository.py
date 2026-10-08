from sqlalchemy import select
from app.extensions import db
from app.models import User


class AuthRepository:
    @staticmethod
    def by_username(username):
        return db.session.scalar(select(User).where(User.username == username))

    @staticmethod
    def by_id(identifier):
        return db.session.get(User, identifier)
