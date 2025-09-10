from . import db  
from datetime import datetime

# tabela Marca
class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(30), unique=True, nullable=False)

# tabela Categoria
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.categ', lazy=True))

    name = db.Column(db.String(30), unique=True, nullable=False)

# tabela cor
class Color(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.cor', lazy=True))
    
    name = db.Column(db.String(20), unique=True, nullable=False)

# tabela tamanho
class Size(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.tamanho', lazy=True))
    
    name = db.Column(db.String(20), unique=True, nullable=False)

# tabela embalagem
class Packaging(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.String(20), nullable=False)
    format = db.Column(db.Integer, nullable=False)
    length = db.Column(db.Numeric(15, 2), nullable=False)
    height = db.Column(db.Numeric(15, 2), nullable=False)
    width = db.Column(db.Numeric(15, 2), nullable=False)

    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.embalagem', lazy=True))

# View da embalagem
class VwPackaging(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dimension = db.Column(db.String(45), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    discount = db.Column(db.Integer, default=0)
    stock = db.Column(db.Integer, nullable=False)
    colors = db.Column(db.Text, nullable=False)
    discription = db.Column(db.Text, nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'), nullable=False)
    marca = db.relationship('Brand', backref=db.backref('marcas', lazy=True))

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    categoria = db.relationship('Category', backref=db.backref('categorias', lazy=True))

    image_1 = db.Column(db.String(150), nullable=False, default='image.jpg')
    image_2 = db.Column(db.String(150), nullable=False, default='image.jpg')
    image_3 = db.Column(db.String(150), nullable=False, default='image.jpg')

    color_id = db.Column(db.Integer, db.ForeignKey('color.id'), nullable=False)
    cor = db.relationship('Color', backref=db.backref('cores', lazy=True))

    size_id = db.Column(db.Integer, db.ForeignKey('size.id'), nullable=False)
    # Combine os relacionamentos e dê a eles um nome único e claro
    # O 'backref' será o nome usado para acessar os produtos a partir de um objeto de tamanho
    size = db.relationship('Size', backref=db.backref('products', lazy=True))

    packaging_id = db.Column(db.Integer, db.ForeignKey('packaging.id'), nullable=False)
    embalagem = db.relationship('Packaging', backref=db.backref('embalagens', lazy=True))

    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    loja = db.relationship('Store', backref=db.backref('lojas.produto', lazy=True))
    type_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<Product %r>' % self.name
    
class VwProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    discount = db.Column(db.Integer, default=0)
    stock = db.Column(db.Integer, nullable=False)
    colors = db.Column(db.Text, nullable=False)
    discription = db.Column(db.Text, nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    brand_id = db.Column(db.Integer, nullable=False)
    nmbrand = db.Column(db.String(30), nullable=False)

    category_id = db.Column(db.Integer,  nullable=False)
    nmcategory = db.Column(db.String(30), nullable=False)

    image_1 = db.Column(db.String(150), nullable=False, default='image.jpg')
    image_2 = db.Column(db.String(150), nullable=False, default='image.jpg')
    image_3 = db.Column(db.String(150), nullable=False, default='image.jpg')

    color_id = db.Column(db.Integer, nullable=False)
    nmcolor = db.Column(db.String(20), nullable=False)

    size_id = db.Column(db.Integer, nullable=False)
    nmsize = db.Column(db.String(20), nullable=False)

    packaging_id = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.String(4), nullable=False)
    format = db.Column(db.Integer, nullable=False)
    length = db.Column(db.Numeric(15, 2), nullable=False)
    height = db.Column(db.Numeric(15, 2), nullable=False)
    width = db.Column(db.Numeric(15, 2), nullable=False)

    store_id = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<VwProduct %r>' % self.name    
    

# tabela loja
class Store(db.Model):
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

# view loja
class VwStore(db.Model):
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
    code = db.Column(db.String(14), nullable=True)
    logo_white = db.Column(db.String(150), nullable=False, default='image.jpg')
    home = db.Column(db.String(1), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "zipcode": self.zipcode,
            "name": self.name,
            "address": self.address,
            "number": self.number,
            "complement": self.complement,
            "neighborhood": self.neighborhood,
            "city": self.city,
            "region": self.region,
            "freight_rate": self.freight_rate,
            "phone": self.phone,
            "pages": self.pages,
            "logo": self.logo,
            "url": self.url,
            "code": self.code,
            "logo_white": self.logo_white,
            "home": self.home}    
    
