from app.extensions import db
from app.models.common import utcnow


class MailOutbox(db.Model):
    __tablename__ = "mail_outbox"
    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey("auth_tokens.id"), nullable=False, unique=True)
    payload = db.Column(db.Text)  # Fernet encrypted; wiped on delivery or final failure.
    status = db.Column(db.String(16), nullable=False, default="pending")
    attempts = db.Column(db.Integer, nullable=False, default=0)
    available_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    finished_at = db.Column(db.DateTime)
    last_error = db.Column(db.String(64))  # Error class only; no addresses, tokens or SMTP replies.
    __table_args__ = (db.Index("ix_mail_outbox_due", "status", "available_at"),)


class AuthRateBucket(db.Model):
    __tablename__ = "auth_rate_buckets"
    key = db.Column(db.String(64), primary_key=True)
    count = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
