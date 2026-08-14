from extension import db
from datetime import datetime


class Quote(db.Model):
    __tablename__ = 'quote'
    __table_args__ = {'schema': 'ouvirtiba'}

    id           = db.Column(db.Integer, primary_key=True)
    number       = db.Column(db.BigInteger, nullable=False, unique=True)
    store_id     = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    client_id    = db.Column(db.Integer, db.ForeignKey('ouvirtiba.client.id'), nullable=False)
    issue_date   = db.Column(db.DateTime, nullable=False, default=datetime.now)
    valid_until  = db.Column(db.DateTime, nullable=True)
    observations = db.Column(db.Text, nullable=True)
    discount     = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total        = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status       = db.Column(db.String(10), nullable=False, default='PENDENTE')
    created_at   = db.Column(db.DateTime, nullable=False, default=datetime.now)

    # Relacionamentos
    client = db.relationship('Client', backref=db.backref('quotes', lazy=True))
    items  = db.relationship('QuoteItem', backref='quote', lazy=True,
                             cascade='all, delete-orphan')


class QuoteItem(db.Model):
    __tablename__ = 'quote_item'
    __table_args__ = {'schema': 'ouvirtiba'}

    id           = db.Column(db.Integer, primary_key=True)
    quote_id     = db.Column(db.Integer, db.ForeignKey('ouvirtiba.quote.id'), nullable=False)
    product_id   = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=True)
    description  = db.Column(db.String(255), nullable=False)
    quantity     = db.Column(db.Numeric(10, 3), nullable=False, default=1)
    unit_price   = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_pct = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    total        = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # Relacionamento opcional com produto
    product = db.relationship('Product', backref=db.backref('quote_items', lazy=True))


class PaymentInstallmentCondition(db.Model):
    __tablename__ = 'payment_installment_condition'
    __table_args__ = (
        db.UniqueConstraint(
            'description', 'installments',
            name='uq_payment_installment_condition_description_installments'
        ),
        db.CheckConstraint('installments > 0', name='chk_payment_installment_condition_installments'),
        db.CheckConstraint('coefficient > 0', name='chk_payment_installment_condition_coefficient'),
        {'schema': 'ouvirtiba'}
    )

    id           = db.Column(db.Integer, primary_key=True)
    description  = db.Column(db.String(100), nullable=False)
    installments = db.Column(db.Integer, nullable=False)
    coefficient  = db.Column(db.Numeric(12, 6), nullable=False)
    active       = db.Column(db.Boolean, nullable=False, default=True)
    created_at   = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at   = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)