# admin/__init__.py
from flask import Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()

# Blueprint com nome único (evita conflito de registro no Flask)
admin_bp = Blueprint(
    'admin_bp',              # <- nome interno único
    __name__,
    url_prefix='/admin',
    template_folder='templates'
)

# importa rotas e models (rotas usa este blueprint já criado)
from . import rotas, models

