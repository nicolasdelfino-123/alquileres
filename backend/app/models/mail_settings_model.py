from app.extensions import db
from app.models.common import utcnow


class MailSettings(db.Model):
    __tablename__ = "mail_settings"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False)
    credentials = db.Column(db.Text, nullable=False)
    registration_code = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
