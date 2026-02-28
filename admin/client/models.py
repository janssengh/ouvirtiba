from datetime import datetime
from extension import db
from sqlalchemy import event # ✅ Importação necessária para os ouvintes de eventos

class Base(db.Model):
    __abstract__ = True
    __table_args__ = {'schema': 'ouvirtiba'}

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

# ==============================================================================
# ✅ NORMALIZAÇÃO AUTOMÁTICA: UPPERCASE PARA TUDO, LOWERCASE PARA EMAIL
# ==============================================================================
@event.listens_for(Client, 'before_insert')
@event.listens_for(Client, 'before_update')
def format_client_strings(mapper, connection, target):
    """
    Percorre todas as colunas de texto da classe Client.
    Transforma email em minúsculo e o restante em maiúsculo.
    """
    # Lista de campos sensíveis que NÃO devem ser alterados (como senhas ou caminhos de imagem)
    ignored_fields = ['password', 'profile'] #

    for column in target.__table__.columns:
        # Só processa se a coluna for do tipo String e não estiver na lista de ignorados
        if isinstance(column.type, db.String) and column.name not in ignored_fields:
            value = getattr(target, column.name)
            
            if value and isinstance(value, str):
                if column.name == 'email':
                    # Exceção para o e-mail: sempre minúsculo
                    setattr(target, column.name, value.lower().strip())
                else:
                    # Todos os outros campos de texto: sempre maiúsculo
                    setattr(target, column.name, value.upper().strip())