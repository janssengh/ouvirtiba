from admin.client.models import Client
from datetime import datetime
from extension import db

class Base(db.Model):
    __abstract__ = True
    __table_args__ = {'schema': 'ouvirtiba'}

# -----------------------------
# Table: Invoice (nota fiscal)
# -----------------------------
class Invoice(Base):
    __tablename__ = 'invoice'

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False, unique=True)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    store_id = db.Column(db.Integer, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.client.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.customer_request.id'), nullable=True)

    total_value = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(1), default='N')  # N=Draft, A=Authorized, C=Cancelled
    xml_file = db.Column(db.String(255), nullable=True)
    pdf_file = db.Column(db.String(255), nullable=True)
    access_key = db.Column(db.String(44), nullable=True)
    series = db.Column(db.Integer, default=1)
    nrec = db.Column(db.String(15))  # deve existir após o ALTER TABLE   
    xml_path = db.Column(db.String(255)) 
    nprot = db.Column(db.Text)
    discount = db.Column(db.Float)

    client = db.relationship('Client', backref='invoices')
    order = db.relationship('Customer_request', backref='invoices')

    def __repr__(self):
        return f"<Invoice #{self.number} - {self.client.name}>"

# -----------------------------
# Table: InvoiceItem (itens da nota)
# -----------------------------
class InvoiceItem(Base):
    __tablename__ = 'invoice_item'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)

    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    ncm = db.Column(db.String(8), nullable=False)
    cfop = db.Column(db.String(4), nullable=False)
    csosn = db.Column(db.String(3), nullable=False)
    discount = db.Column(db.Float)
    serialnumber = db.Column(db.String(15))

    invoice = db.relationship('Invoice', backref='items')
    product = db.relationship('Product', backref='invoice_items')
    
    def __repr__(self):
        return f"<InvoiceItem {self.product.name} x {self.quantity}>"
    
# ================================================================
# MODELO PARA CONTROLE DE SEQUÊNCIA DE NOTAS FISCAIS
# ================================================================
# Adicione este modelo ao arquivo admin/nfe/models.py

class InvoiceSequence(Base):
    """
    Controla a sequência numérica das notas fiscais por loja e série.
    Garante numeração sequencial e crescente para cada combinação store_id + series.
    """
    __tablename__ = 'invoice_sequence'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    series = db.Column(db.Integer, nullable=False, default=1)
    last_number = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraint única para garantir um registro por loja + série
    __table_args__ = (
        db.UniqueConstraint('store_id', 'series', name='uq_invoice_sequence_store_series'),
        {'schema': 'ouvirtiba'}
    )
    
    def __repr__(self):
        return f'<InvoiceSequence store_id={self.store_id} series={self.series} last_number={self.last_number}>'
