# admin/order/models.py
from datetime import datetime
from extension import db
from admin.client.models import Client

class Base(db.Model):
    __abstract__ = True
    __table_args__ = {'schema': 'ouvirtiba'}

class Customer_request(Base):
    __tablename__ = 'customer_request'

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, nullable=False)
    number = db.Column(db.BigInteger, nullable=False)  
    client_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.client.id'), nullable=False)
    created_at = db.Column(db.DateTime(50), default=datetime.now, nullable=False)
    payment_form = db.Column(db.Integer, nullable=False)
    payment_condition = db.Column(db.Integer, nullable=False)
    payment_amount_inp = db.Column(db.Numeric(15,2), nullable=False)
    payment_form_inp = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(15,2), nullable=False)
    observation = db.Column(db.String(510), nullable=True)
    status = db.Column(db.String(2), default='N', nullable=True)

    # relacionamento com Client
    client = db.relationship('Client', backref='orders', lazy=True)

    # ✅ relacionamento com itens de pedido
    items = db.relationship('Customer_request_item', backref='order', lazy=True, cascade="all, delete-orphan")


class Customer_request_item(Base):
    __tablename__ = 'customer_request_item'

    id = db.Column(db.Integer, primary_key=True)
    customer_request_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.customer_request.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(15,2), nullable=False)
    discount = db.Column(db.Numeric(15,2), default=0)
    amount_initial = db.Column(db.Numeric(15,2), nullable=False)
    amount = db.Column(db.Numeric(15,2), nullable=False)
    serialnumber = db.Column(db.String(15), nullable=True)

    # relacionamento com Customer_request
    orderitem = db.relationship('Customer_request', backref='ordersitem', lazy=True)

    # relacionamento com Product
    product = db.relationship('Product', backref='orders', lazy=True)
