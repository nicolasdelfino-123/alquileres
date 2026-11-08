from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def business_today():
    return datetime.now(ZoneInfo("America/Argentina/Cordoba")).date()


class CancellationMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)


ZERO = Decimal("0.00")
