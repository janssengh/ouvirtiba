from extension import db
from datetime import datetime

class ProductAssembly(db.Model):
    __tablename__ = 'product_assembly'
    __table_args__ = {'schema': 'ouvirtiba'}

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)

    # ALTERADO: agora o parent será o base_unit
    parent_product_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=True)

    base_unit_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)
    receptor_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)
    oliva_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=False)
    carregador_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.product.id'), nullable=True)

    quantity = db.Column(db.Integer, nullable=False, default=1)

    # Preço total informado
    sale_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    # NOVAS COLUNAS
    selling_price_base = db.Column(db.Numeric(10, 2), nullable=True)
    selling_price_receptor = db.Column(db.Numeric(10, 2), nullable=True)
    selling_price_oliva = db.Column(db.Numeric(10, 2), nullable=True)
    selling_price_carregador = db.Column(db.Numeric(10, 2), nullable=True)

    status = db.Column(db.String(20), nullable=False, default='CONCLUIDO')
    assembly_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamentos
    parent = db.relationship('Product', foreign_keys=[parent_product_id])
    base = db.relationship('Product', foreign_keys=[base_unit_id])
    receptor = db.relationship('Product', foreign_keys=[receptor_id])
    oliva = db.relationship('Product', foreign_keys=[oliva_id])
    carregador = db.relationship('Product', foreign_keys=[carregador_id])