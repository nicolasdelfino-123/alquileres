"""Contract acquisition fees are agency income, never tenant rent or owner funds."""
from app.extensions import db
from app.models.common import CancellationMixin, utcnow


class ContractFee(CancellationMixin, db.Model):
    __tablename__ = 'contract_fees'
    __table_args__ = (db.CheckConstraint('amount > 0', name='ck_contract_fee_amount'),
                     db.CheckConstraint("payer IN ('tenant','owner')", name='ck_contract_fee_payer'))
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('rental_contracts.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    payer = db.Column(db.String(20), nullable=False)
    agreed_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payments = db.relationship('ContractFeePayment', back_populates='fee')


class ContractFeePayment(CancellationMixin, db.Model):
    __tablename__ = 'contract_fee_payments'
    __table_args__ = (db.CheckConstraint('amount > 0', name='ck_fee_payment_amount'),)
    id = db.Column(db.Integer, primary_key=True)
    fee_id = db.Column(db.Integer, db.ForeignKey('contract_fees.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, index=True)
    method = db.Column(db.String(30), nullable=False)
    reference = db.Column(db.String(150))
    idempotency_key = db.Column(db.String(100), nullable=False, unique=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fee = db.relationship('ContractFee', back_populates='payments')


class OfficialIndex(db.Model):
    __tablename__ = 'official_indices'
    __table_args__ = (db.UniqueConstraint('kind', 'value_date', name='uq_official_index_day'),
                     db.CheckConstraint('value > 0', name='ck_official_index_positive'))
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(3), nullable=False)
    value_date = db.Column(db.Date, nullable=False)
    value = db.Column(db.Numeric(24, 10), nullable=False)
    source_url = db.Column(db.String(500), nullable=False)
    fetched_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class AdjustmentQuote(db.Model):
    __tablename__ = 'adjustment_quotes'
    id = db.Column(db.String(32), primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('rental_contracts.id'), nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    effective_date = db.Column(db.Date, nullable=False)
    base_amount = db.Column(db.Numeric(12, 2), nullable=False)
    detail = db.Column(db.JSON, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
