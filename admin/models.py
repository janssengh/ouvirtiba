from sqlalchemy import MetaData, event # ✅ Importação necessária para os eventos
from datetime import datetime
from extension import db 

# =========================================================
# 1. CLASSE BASE ABSTRATA (MIXIN)
class Base(db.Model):
    __abstract__ = True
    __table_args__ = {'schema': 'ouvirtiba'}
# =========================================================

class User(Base):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=False, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(180), unique=False, nullable=False)
    profile = db.Column(db.String(180), unique=False, nullable=False, default='profile.jpg')
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.user', lazy=True))

class Store(Base):
    id = db.Column(db.Integer, primary_key=True)
    zipcode = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(45), nullable=False)
    address = db.Column(db.String(50), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    complement = db.Column(db.String(45), nullable=True)
    neighborhood = db.Column(db.String(45), nullable=False)
    city = db.Column(db.String(45), nullable=False)
    region = db.Column(db.String(15), nullable=False)
    freight_rate = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    pages = db.Column(db.Integer, nullable=False)
    logo = db.Column(db.String(150), nullable=False, default='image.jpg')
    url = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(14), nullable=False)
    logo_white = db.Column(db.String(150), nullable=False, default='image.jpg')
    home = db.Column(db.String(1), nullable=False, default='N')
    state_registration = db.Column(db.String(20))

class Brand(Base):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(30), unique=True, nullable=False)

class Category(Base):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    name = db.Column(db.String(30), unique=True, nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.categ', lazy=True))

class Color(Base):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    name = db.Column(db.String(20), unique=True, nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.cor', lazy=True))

class Size(Base):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    name = db.Column(db.String(20), unique=True, nullable=False)   
    loja = db.relationship('Store', backref=db.backref('lojas.tamanho', lazy=True))

class Packaging(Base):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.String(20), nullable=False)
    format = db.Column(db.Integer, nullable=False)
    length = db.Column(db.Numeric(15, 2), nullable=False)
    height = db.Column(db.Numeric(15, 2), nullable=False)
    width = db.Column(db.Numeric(15, 2), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.embalagem', lazy=True))

    @property
    def dimension(self):
        """Retorna uma string formatada com as dimensões."""
        return f"{self.format}(F) - {self.length}(C)x{self.width}(L)x{self.height}(A) ({self.weight}kg)"


class Product(Base):

    @property
    def type_name(self):
        """Retorna o nome do tipo de produto."""
        if self.type_id == 1:
            return "Aparelhos Auditivos"
        elif self.type_id == 2:
            return "Acessórios"
        elif self.type_id == 3:
            return "Produto Acabado"
        else:
            return "Outros"
    
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    type_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    discount = db.Column(db.Integer, default=0)
    stock = db.Column(db.Integer, nullable=False)
    colors = db.Column(db.Text, nullable=False)
    discription = db.Column(db.Text, nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    brand_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.brand.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.category.id'), nullable=False)
    image_1 = db.Column(db.String(150), nullable=False, default='image.jpg')
    image_2 = db.Column(db.String(150), nullable=False, default='image.jpg')
    image_3 = db.Column(db.String(150), nullable=False, default='image.jpg')
    color_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.color.id'), nullable=False)
    size_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.size.id'), nullable=False)
    packaging_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.packaging.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)

    marca = db.relationship('Brand', backref=db.backref('marcas', lazy=True))
    categoria = db.relationship('Category', backref=db.backref('categorias', lazy=True))
    cor = db.relationship('Color', backref=db.backref('cores', lazy=True))
    nmsize = db.relationship('Size', backref=db.backref('sizes', lazy=True))
    tamanho = db.relationship('Size', backref=db.backref('tamanhos', lazy=True))
    embalagem = db.relationship('Packaging', backref=db.backref('embalagens', lazy=True))
    loja = db.relationship('Store', backref=db.backref('lojas.produto', lazy=True))

# ==============================================================================
# ✅ LÓGICA DE NORMALIZAÇÃO GLOBAL (UPPERCASE / LOWERCASE)
# ==============================================================================

def global_auto_format(mapper, connection, target):
    """
    Formata strings automaticamente antes de salvar no banco.
    """
    # Campos que devem ser preservados (senhas e arquivos)
    ignored = ['password', 'profile', 'logo', 'logo_white', 'image_1', 'image_2', 'image_3', 'url']

    for column in target.__table__.columns:
        # Verifica se é coluna de texto (String ou Text)
        if isinstance(column.type, (db.String, db.Text)) and column.name not in ignored:
            value = getattr(target, column.name)
            
            if value and isinstance(value, str):
                # E-mail e Usuário ficam em minúsculo
                if column.name in ['email', 'username']:
                    setattr(target, column.name, value.lower().strip())
                # Restante fica em MAIÚSCULO
                else:
                    setattr(target, column.name, value.upper().strip())

# Lista de todas as classes para aplicar a regra
all_models = [User, Store, Brand, Category, Color, Size, Packaging, Product]

for model in all_models:
    event.listens_for(model, 'before_insert')(global_auto_format)
    event.listens_for(model, 'before_update')(global_auto_format)