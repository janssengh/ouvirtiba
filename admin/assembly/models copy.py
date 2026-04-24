from extension import db
from datetime import datetime

class ProductAssembly(db.Model):
    __tablename__ = 'product_assembly'
    __table_args__ = {'schema': 'ouvirtiba'}

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    parent_product_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=True)
    base_unit_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)
    receptor_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)
    oliva_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)

    quantity = db.Column(db.Integer, nullable=False, default=1)
    sale_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)  # Preço de venda informado na montagem
    status = db.Column(db.String(20), nullable=False, default='CONCLUIDO')
    assembly_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamentos para facilitar exibição
    parent = db.relationship('Product', foreign_keys=[parent_product_id])
    base = db.relationship('Product', foreign_keys=[base_unit_id])
    receptor = db.relationship('Product', foreign_keys=[receptor_id])
    oliva = db.relationship('Product', foreign_keys=[oliva_id])