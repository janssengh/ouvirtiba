# admin/purchases/models.py

from datetime import datetime
from extension import db

# =========================================================
# CLASSE BASE ABSTRATA (MIXIN)
# =========================================================
class Base(db.Model):
    __abstract__ = True
    __table_args__ = {'schema': 'ouvirtiba'}

# =========================================================
# MODEL FORNECEDOR (SUPPLIER)
# =========================================================
class Supplier(Base):
    __tablename__ = 'supplier'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    tax_id = db.Column(db.String(14), nullable=False)  # CNPJ
    corporate_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    # Relacionamentos
    invoices = db.relationship('PurchaseInvoice', back_populates='supplier', lazy=True)
    
    # Constraint única: store_id + tax_id
    __table_args__ = (
        db.UniqueConstraint('store_id', 'tax_id', name='uq_supplier_store_tax_id'),
        {'schema': 'ouvirtiba'}
    )
    
    def __repr__(self):
        return f'<Supplier {self.corporate_name}>'

# =========================================================
# MODEL NOTA DE ENTRADA (PURCHASE INVOICE)
# =========================================================
class PurchaseInvoice(Base):
    __tablename__ = 'purchase_invoice'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.supplier.id'), nullable=False)
    receipt_date = db.Column(db.Date, nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    entry_exit_date = db.Column(db.Date, nullable=False)
    invoice_number = db.Column(db.String(20), nullable=False)
    series = db.Column(db.String(10), nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    total_discount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.String(20), default='Finalizada') # Finalizada
    
    # Relacionamentos
    supplier = db.relationship('Supplier', back_populates='invoices')
    items = db.relationship('PurchaseInvoiceItem', back_populates='invoice', cascade='all, delete-orphan', lazy=True)
    
    # Constraint única: store_id + supplier_id + invoice_number + series
    __table_args__ = (
        db.UniqueConstraint('store_id', 'supplier_id', 'invoice_number', 'series', name='uq_invoice_unique'),
        {'schema': 'ouvirtiba'}
    )
    
    def __repr__(self):
        return f'<PurchaseInvoice NF:{self.invoice_number}/{self.series}>'


# =========================================================
# MODEL ITEM DA NOTA DE ENTRADA (PURCHASE INVOICE ITEM)
# =========================================================
class PurchaseInvoiceItem(Base):
    __tablename__ = 'purchase_invoice_item'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_invoice_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.purchase_invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)
    supplier_product_code = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    discount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    
    # Relacionamentos
    invoice = db.relationship('PurchaseInvoice', back_populates='items')
    product = db.relationship('Product')
    
    # Constraint única: purchase_invoice_id + product_id
    __table_args__ = (
        db.UniqueConstraint('purchase_invoice_id', 'product_id', name='uq_invoice_product'),
        {'schema': 'ouvirtiba'}
    )
    
    def __repr__(self):
        return f'<PurchaseInvoiceItem Invoice:{self.purchase_invoice_id} Product:{self.product_id}>'