
from sqlalchemy import MetaData
from datetime import datetime
from extension import db # ✅ ADICIONE: Importa a instância 'db' do extension.py

# Define schema padrão
#metadata = MetaData(schema="ouvirtiba")
# ✅ REMOVA ESTA LINHA CONFLITANTE:
#db = SQLAlchemy(metadata=metadata)

# =========================================================
# 1. CLASSE BASE ABSTRATA (MIXIN)
# Esta classe define o esquema e é abstrata (não cria uma tabela no banco).
class Base(db.Model):
    __abstract__ = True
    __table_args__ = {'schema': 'ouvirtiba'} # ✅ Aplica o esquema em todas as classes herdeiras!
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

    def __repr__(self):
        return '<User %r>' % self.user


# tabela loja
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

    def __init__(self, zipcode, name, address, number, complement, neighborhood,
                 city, region, freight_rate, phone, pages, logo, url, code, logo_white, home):
        self.zipcode = zipcode
        self.name = name
        self.address = address
        self.number = number
        self.complement = complement
        self.neighborhood = neighborhood
        self.city = city
        self.region = region
        self.freight_rate = freight_rate
        self.phone = phone
        self.pages = pages
        self.logo = logo
        self.url = url
        self.code = code
        self.logo_white = logo_white
        self.home = home

# tabela Marca
class Brand(Base):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(30), unique=True, nullable=False)

# tabela Categoria
class Category(Base):
    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.categ', lazy=True))

    name = db.Column(db.String(30), unique=True, nullable=False)

# tabela cor
class Color(Base):
    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.cor', lazy=True))
    
    name = db.Column(db.String(20), unique=True, nullable=False)

# tabela tamanho
class Size(Base):
    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.tamanho', lazy=True))
    
    name = db.Column(db.String(20), unique=True, nullable=False)   

# tabela embalagem
class Packaging(Base):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.String(20), nullable=False)
    format = db.Column(db.Integer, nullable=False)
    length = db.Column(db.Numeric(15, 2), nullable=False)
    height = db.Column(db.Numeric(15, 2), nullable=False)
    width = db.Column(db.Numeric(15, 2), nullable=False)

    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.embalagem', lazy=True))    

class Product(Base):
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
    marca = db.relationship('Brand', backref=db.backref('marcas', lazy=True))

    category_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.category.id'), nullable=False)
    categoria = db.relationship('Category', backref=db.backref('categorias', lazy=True))

    image_1 = db.Column(db.String(150), nullable=False, default='image.jpg')
    image_2 = db.Column(db.String(150), nullable=False, default='image.jpg')
    image_3 = db.Column(db.String(150), nullable=False, default='image.jpg')

    color_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.color.id'), nullable=False)
    cor = db.relationship('Color', backref=db.backref('cores', lazy=True))

    size_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.size.id'), nullable=False)
    nmsize = db.relationship('Size', backref=db.backref('sizes', lazy=True))
    tamanho = db.relationship('Size', backref=db.backref('tamanhos', lazy=True))
    packaging_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.packaging.id'), nullable=False)
    embalagem = db.relationship('Packaging', backref=db.backref('embalagens', lazy=True))

    store_id = db.Column(db.Integer, db.ForeignKey('ouvirtiba.store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.produto', lazy=True))
    type_id = db.Column(db.Integer, nullable=False)    


