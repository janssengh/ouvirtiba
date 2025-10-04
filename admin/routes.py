from flask import Blueprint, render_template
from .models import Product, db

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')

@admin_bp.route('/')
def product_list():
    products = Product.query.all()
    return render_template('admin/product_list.html', products=products)
