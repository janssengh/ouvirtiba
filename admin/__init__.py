from flask import Blueprint
from .routes import admin_bp, auth_bp
#from extension import db, bcrypt  # ✅ importa do módulo central

def init_app(app):
    #db.init_app(app)
    #bcrypt.init_app(app)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    # ✅ ADICIONE ESTA LINHA PARA REGISTRAR O BLUEPRINT DE AUTENTICAÇÃO
    app.register_blueprint(auth_bp, url_prefix="/auth") 

