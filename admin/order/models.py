# admin/order/models.py
from datetime import datetime
from extension import db
from admin.client.models import Client
from sqlalchemy import event  # ✅ Importação necessária


class Base(db.Model):
    __abstract__ = True
    __table_args__ = {'schema': 'ouvirtiba'}


class Customer_request(Base):
    __tablename__ = 'customer_request'

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, nullable=False)
    number = db.Column(db.BigInteger, nullable=False)

    # ─── NOVO: tipo do documento ────────────────────────────────────────────────
    # 'PED' = Pedido de Venda (comportamento original)
    # 'TEG' = Termo de Entrega em Garantia  (sem cobrança, saída de estoque)
    # 'OVG' = Ordem de Serviço c/ Garantia de Venda (venda de peça, saída de estoque)
    doc_type = db.Column(db.String(3), default='PED', nullable=False)

    client_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.client.id'), nullable=False)
    created_at = db.Column(db.DateTime(50), default=datetime.now, nullable=False)

    # ─── NOVO: data de emissão informada pelo usuário ───────────────────────────
    # Para TEG e OVG o usuário informa a data; para PED é igual ao created_at
    issued_at = db.Column(db.DateTime, nullable=True)

    # ─── NOVO: nº da nota fiscal do fornecedor (somente TEG) ────────────────────
    supplier_invoice = db.Column(db.String(30), nullable=True)

    payment_form = db.Column(db.Integer, nullable=False)
    payment_condition = db.Column(db.Integer, nullable=False)
    payment_amount_inp = db.Column(db.Numeric(15, 2), nullable=False)
    payment_form_inp = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    observation = db.Column(db.String(510), nullable=True)
    status = db.Column(db.String(2), default='N', nullable=True)
    is_invoiced = db.Column(db.String(1), default='N')
    discount = db.Column(db.Numeric(15, 2), nullable=True)

    client = db.relationship('Client', backref='orders', lazy=True)
    items = db.relationship(
        'Customer_request_item', backref='order', lazy=True, cascade="all, delete-orphan"
    )


class Customer_request_item(Base):
    __tablename__ = 'customer_request_item'

    id = db.Column(db.Integer, primary_key=True)
    customer_request_id = db.Column(
        db.Integer, db.ForeignKey('ouvirtiba.customer_request.id'), nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(15, 2), nullable=False)
    discount = db.Column(db.Numeric(15, 2), default=0)
    amount_initial = db.Column(db.Numeric(15, 2), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    serialnumber = db.Column(db.String(15), nullable=True)

    orderitem = db.relationship('Customer_request', backref='ordersitem', lazy=True)
    product = db.relationship('Product', backref='orders', lazy=True)


# ==============================================================================
# ✅ Script de migração — execute UMA vez no banco para adicionar os novos campos
# ==============================================================================
# ALTER TABLE ouvirtiba.customer_request
#   ADD COLUMN IF NOT EXISTS doc_type        VARCHAR(3)  NOT NULL DEFAULT 'PED',
#   ADD COLUMN IF NOT EXISTS issued_at       TIMESTAMP,
#   ADD COLUMN IF NOT EXISTS supplier_invoice VARCHAR(30);
# ==============================================================================


# ==============================================================================
# ✅ NORMALIZAÇÃO AUTOMÁTICA PARA PEDIDOS E ITENS
# ==============================================================================

def format_strings_event(mapper, connection, target):
    """Função genérica para formatar strings antes de salvar"""
    for column in target.__table__.columns:
        if isinstance(column.type, db.String):
            value = getattr(target, column.name)
            if value and isinstance(value, str):
                setattr(target, column.name, value.upper().strip())


event.listens_for(Customer_request, 'before_insert')(format_strings_event)
event.listens_for(Customer_request, 'before_update')(format_strings_event)
event.listens_for(Customer_request_item, 'before_insert')(format_strings_event)
event.listens_for(Customer_request_item, 'before_update')(format_strings_event)