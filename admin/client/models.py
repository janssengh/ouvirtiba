from datetime import datetime
from extension import db


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

class Client(Base):
    __tablename__ = 'client'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(14), unique=True, nullable=False)
    store_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=True, unique=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    profile = db.Column(db.String(50), nullable=True, default='profile.jpg')
    zipcode = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(50), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    complement = db.Column(db.String(45), nullable=True)
    neighborhood = db.Column(db.String(45), nullable=False)
    city = db.Column(db.String(45), nullable=False)
    region = db.Column(db.String(15), nullable=False)
    country = db.Column(db.String(45), nullable=False, default='Brasil')
    password = db.Column(db.String(255), nullable=True)
    type = db.Column(db.String(2), nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    contact = db.Column(db.String(50), nullable=False)
    administrator = db.Column(db.String(1), nullable=True, default='N')
