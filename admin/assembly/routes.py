from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from extension import db
from admin.models import Product, Category
from .models import ProductAssembly
from .forms import FormProductAssembly

from datetime import datetime, timedelta
from decimal import Decimal
import math

assembly_bp = Blueprint('assembly_bp', __name__, template_folder='templates')


@assembly_bp.route('/admin/assembly/list')
def assembly_list():
    store_id = session.get('store_id')
    assemblies = ProductAssembly.query.filter_by(store_id=store_id).order_by(ProductAssembly.assembly_date.desc()).all()
    return render_template('admin/assembly/product_assembly_list.html', assemblies=assemblies)


@assembly_bp.route('/admin/assembly/create', methods=['GET', 'POST'])
def assembly_create():
    form = FormProductAssembly()
    store_id = session.get('store_id')

    # Filtros para os componentes
    base_units = Product.query.filter(Product.type_id == 1, Product.stock > 0, Product.store_id == store_id).all()
    form.base_unit_id.choices = [
        (p.id, f"{p.name} | {p.colors} (Estoque: {p.stock})")
        for p in base_units
    ]

    receptors = Product.query.join(Category).filter(Product.type_id == 2, Product.stock > 0, Category.name.ilike('receptores')).all()
    form.receptor_id.choices = [(p.id, f"{p.name} (Estoque: {p.stock})") for p in receptors]

    olivas = Product.query.join(Category).filter(Product.type_id == 2, Product.stock > 0, Category.name.ilike('olivas')).all()
    form.oliva_id.choices = [(p.id, f"{p.name} (Estoque: {p.stock})") for p in olivas]

    show_confirmation = False
    suggested_name  = ""
    suggested_price = 0.0
    rateio_base     = 0
    rateio_receptor = 0
    rateio_oliva    = 0

    if request.method == 'POST':

        # ------------------------------------------------------------------ #
        # PASSO 1 — Gerar sugestão de nome e exibir rateio                   #
        # ------------------------------------------------------------------ #
        if 'btn_gerar' in request.form:
            base     = Product.query.get(form.base_unit_id.data)
            receptor = Product.query.get(form.receptor_id.data)
            oliva    = Product.query.get(form.oliva_id.data)

            suggested_name  = f"{base.name} {receptor.name} {oliva.name}"
            suggested_price = float(base.price)

            custo_base     = float(base.price or 0)
            custo_receptor = float(receptor.price or 0)
            custo_oliva    = float(oliva.price or 0)
            custo_total    = custo_base + custo_receptor + custo_oliva

            if custo_total > 0:
                rateio_base     = math.floor(suggested_price * custo_base     / custo_total)
                rateio_receptor = math.floor(suggested_price * custo_receptor / custo_total)
                rateio_oliva    = int(suggested_price) - rateio_base - rateio_receptor
            else:
                rateio_base = int(suggested_price)

            show_confirmation = True

        # ------------------------------------------------------------------ #
        # PASSO 2 — Finalizar montagem                                       #
        # ------------------------------------------------------------------ #
        elif 'btn_finalizar' in request.form:
            try:
                qty         = int(request.form.get('final_qty', 1))
                final_name  = request.form.get('final_name')
                final_price = float(request.form.get('final_price', 0).replace(',', '.'))

                base     = Product.query.get(form.base_unit_id.data)
                receptor = Product.query.get(form.receptor_id.data)
                oliva    = Product.query.get(form.oliva_id.data)

                # Rateio proporcional ao price de cada componente — valores inteiros
                custo_base     = float(base.price or 0)
                custo_receptor = float(receptor.price or 0)
                custo_oliva    = float(oliva.price or 0)
                custo_total    = custo_base + custo_receptor + custo_oliva

                if custo_total > 0:
                    preco_base     = math.floor(final_price * custo_base     / custo_total)
                    preco_receptor = math.floor(final_price * custo_receptor / custo_total)
                    preco_oliva    = int(final_price) - preco_base - preco_receptor
                else:
                    preco_base, preco_receptor, preco_oliva = int(final_price), 0, 0

                data_local = datetime.now() - timedelta(hours=3)

                # --- Produto acabado: CORPO -------------------------------- #
                prod_base = Product(
                    name=base.name,
                    type_id=3,
                    stock=qty,
                    price=preco_base,
                    brand_id=base.brand_id,
                    category_id=base.category_id,
                    color_id=base.color_id,
                    size_id=base.size_id,
                    store_id=store_id,
                    image_1=base.image_1,
                    image_2=base.image_2,
                    image_3=base.image_3,
                    discription=base.discription,
                    colors=base.colors,
                    packaging_id=base.packaging_id,
                    pub_date=data_local
                )

                # --- Produto acabado: RECEPTOR ----------------------------- #
                prod_receptor = Product(
                    name=receptor.name,
                    type_id=3,
                    stock=qty,
                    price=preco_receptor,
                    brand_id=receptor.brand_id,
                    category_id=receptor.category_id,
                    color_id=receptor.color_id,
                    size_id=receptor.size_id,
                    store_id=store_id,
                    image_1=receptor.image_1,
                    image_2=receptor.image_2,
                    image_3=receptor.image_3,
                    discription=receptor.discription,
                    colors=receptor.colors,
                    packaging_id=receptor.packaging_id,
                    pub_date=data_local
                )

                # --- Produto acabado: OLIVA -------------------------------- #
                prod_oliva = Product(
                    name=oliva.name,
                    type_id=3,
                    stock=qty,
                    price=preco_oliva,
                    brand_id=oliva.brand_id,
                    category_id=oliva.category_id,
                    color_id=oliva.color_id,
                    size_id=oliva.size_id,
                    store_id=store_id,
                    image_1=oliva.image_1,
                    image_2=oliva.image_2,
                    image_3=oliva.image_3,
                    discription=oliva.discription,
                    colors=oliva.colors,
                    packaging_id=oliva.packaging_id,
                    pub_date=data_local
                )

                db.session.add_all([prod_base, prod_receptor, prod_oliva])
                db.session.flush()  # gera os IDs

                # --- Registro na tabela assembly --------------------------- #
                new_assembly = ProductAssembly(
                    store_id=store_id,
                    parent_product_id=prod_base.id,
                    base_unit_id=base.id,
                    receptor_id=receptor.id,
                    oliva_id=oliva.id,
                    quantity=qty,
                    sale_price=Decimal(str(int(final_price))),
                    status='CONCLUIDO',
                    assembly_date=data_local
                )
                db.session.add(new_assembly)

                # --- Baixa de estoque dos componentes ---------------------- #
                base.stock     -= qty
                receptor.stock -= qty
                oliva.stock    -= qty

                db.session.commit()
                flash(
                    f'Montagem concluída! '
                    f'"{prod_base.name}" R$ {preco_base}, '
                    f'"{prod_receptor.name}" R$ {preco_receptor}, '
                    f'"{prod_oliva.name}" R$ {preco_oliva}. '
                    f'Total: R$ {int(final_price)}.',
                    'success'
                )
                return redirect(url_for('assembly_bp.assembly_list'))

            except Exception as e:
                db.session.rollback()
                flash(f'Erro: {str(e)}', 'danger')

    return render_template(
        'admin/assembly/product_assembly_create.html',
        form=form,
        show_confirmation=show_confirmation,
        suggested_name=suggested_name,
        suggested_price=suggested_price,
        rateio_base=rateio_base,
        rateio_receptor=rateio_receptor,
        rateio_oliva=rateio_oliva,
    )