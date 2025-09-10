# admin/rotas.py
from flask import render_template
from .models import Product
from . import admin_bp  # usa o blueprint criado em __init__.py

@admin_bp.route('/')
def index():
    produtos = Product.query.order_by(
        Product.type_id.asc(),
        Product.name.asc(),
        Product.stock.desc()
    ).all()
    return render_template(
        'listaprod.html',
        titulo="Produtos/Acessórios",
        produtos=produtos
    )
