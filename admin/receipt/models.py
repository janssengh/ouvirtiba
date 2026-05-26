from extension import db
from datetime import datetime


class Receipt(db.Model):
    __tablename__ = 'receipt'
    __table_args__ = {'schema': 'ouvirtiba'}

    id             = db.Column(db.Integer, primary_key=True)
    number         = db.Column(db.BigInteger, nullable=False, unique=True)
    store_id       = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    client_id      = db.Column(db.Integer, db.ForeignKey('ouvirtiba.client.id'), nullable=False)
    issue_date     = db.Column(db.DateTime, nullable=False, default=datetime.now)
    payment_method = db.Column(db.String(30), nullable=False, default='DINHEIRO')
    observations   = db.Column(db.Text, nullable=True)
    total          = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    # Status: GERADO → recibo criado no sistema
    #         EMITIDO → PDF gerado e entregue ao cliente
    #         CANCELADO → cancelado
    status         = db.Column(db.String(10), nullable=False, default='GERADO')
    created_at     = db.Column(db.DateTime, nullable=False, default=datetime.now)

    client = db.relationship('Client', backref=db.backref('receipts', lazy=True))
    items  = db.relationship('ReceiptItem', backref='receipt', lazy=True,
                             cascade='all, delete-orphan')


class ReceiptItem(db.Model):
    __tablename__ = 'receipt_item'
    __table_args__ = {'schema': 'ouvirtiba'}

    id          = db.Column(db.Integer, primary_key=True)
    receipt_id  = db.Column(db.Integer, db.ForeignKey('ouvirtiba.receipt.id'), nullable=False)
    product_id  = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=True)
    description = db.Column(db.String(255), nullable=False)
    quantity    = db.Column(db.Numeric(10, 3), nullable=False, default=1)
    unit_price  = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total       = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    product = db.relationship('Product', backref=db.backref('receipt_items', lazy=True))