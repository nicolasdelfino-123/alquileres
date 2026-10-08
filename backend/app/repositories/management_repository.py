from sqlalchemy import select
from app.extensions import db


class ManagementRepository:
    @staticmethod
    def get(model, identifier, lock=False):
        statement = select(model).where(model.id == identifier)
        if lock:
            statement = statement.with_for_update()
        return db.session.execute(statement.execution_options(populate_existing=lock)).scalar_one_or_none()

    @staticmethod
    def list(model, filters=None):
        statement = select(model).order_by(model.id)
        for field, value in (filters or {}).items():
            statement = statement.where(getattr(model, field) == value)
        return list(db.session.scalars(statement))

    @staticmethod
    def add(record):
        db.session.add(record)
        db.session.flush()
        return record

    @staticmethod
    def delete(record):
        db.session.delete(record)
        db.session.flush()
