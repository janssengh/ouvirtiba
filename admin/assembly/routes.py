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

    base_units = Product.query.filter(Product.type_id == 1, Product.stock > 0, Product.store_id == store_id).all()
    form.base_unit_id.choices = [(p.id, f"{p.name} | {p.colors} (Estoque: {p.stock})") for p in base_units]

    receptors = Product.query.join(Category).filter(Product.type_id == 2, Product.stock > 0, Category.name.ilike('receptores')).all()
    form.receptor_id.choices = [(p.id, f"{p.name} (Estoque: {p.stock})") for p in receptors]

    olivas = Product.query.join(Category).filter(Product.type_id == 2, Product.stock > 0, Category.name.ilike('olivas')).all()
    form.oliva_id.choices = [(p.id, f"{p.name} (Estoque: {p.stock})") for p in olivas]

    carregadores = Product.query.join(Category).filter(Product.type_id == 2, Product.stock > 0, Category.name.ilike('carregadores')).all()
    form.carregador_id.choices = [(0, '— Sem carregador —')] + [(p.id, f"{p.name} (Estoque: {p.stock})") for p in carregadores]

    show_confirmation = False
    suggested_name  = ""
    suggested_price = 0.0
    rateio_base     = 0
    rateio_receptor = 0
    rateio_oliva    = 0
    rateio_carregador = 0
    carregador_selecionado = False

    if request.method == 'POST':

        # PASSO 1
        if 'btn_gerar' in request.form:
            base     = Product.query.get(form.base_unit_id.data)
            receptor = Product.query.get(form.receptor_id.data)
            oliva    = Product.query.get(form.oliva_id.data)

            carregador_id = form.carregador_id.data
            carregador = Product.query.get(carregador_id) if carregador_id else None
            carregador_selecionado = carregador is not None

            suggested_name  = f"{base.name} {receptor.name} {oliva.name}"
            suggested_price = float(base.price)

            custo_base      = float(base.price or 0)
            custo_receptor  = float(receptor.price or 0)
            custo_oliva     = float(oliva.price or 0)
            custo_carregador = float(carregador.price or 0) if carregador else 0
            custo_total     = custo_base + custo_receptor + custo_oliva + custo_carregador

            if custo_total > 0:
                rateio_base      = math.floor(suggested_price * custo_base / custo_total)
                rateio_receptor  = math.floor(suggested_price * custo_receptor / custo_total)
                rateio_carregador = math.floor(suggested_price * custo_carregador / custo_total) if carregador else 0
                rateio_oliva     = int(suggested_price) - rateio_base - rateio_receptor - rateio_carregador
            else:
                rateio_base = int(suggested_price)

            show_confirmation = True

        # PASSO 2
        elif 'btn_finalizar' in request.form:
            try:
                qty         = int(request.form.get('final_qty', 1))
                final_price = float(request.form.get('final_price', 0).replace(',', '.'))

                base     = Product.query.get(form.base_unit_id.data)
                receptor = Product.query.get(form.receptor_id.data)
                oliva    = Product.query.get(form.oliva_id.data)

                carregador_id = form.carregador_id.data
                carregador = Product.query.get(carregador_id) if carregador_id else None

                custo_base       = float(base.price or 0)
                custo_receptor   = float(receptor.price or 0)
                custo_oliva      = float(oliva.price or 0)
                custo_carregador = float(carregador.price or 0) if carregador else 0
                custo_total      = custo_base + custo_receptor + custo_oliva + custo_carregador

                if custo_total > 0:
                    preco_base       = math.floor(final_price * custo_base / custo_total)
                    preco_receptor   = math.floor(final_price * custo_receptor / custo_total)
                    preco_carregador = math.floor(final_price * custo_carregador / custo_total) if carregador else 0
                    preco_oliva      = int(final_price) - preco_base - preco_receptor - preco_carregador
                else:
                    preco_base, preco_receptor, preco_oliva, preco_carregador = int(final_price), 0, 0, 0

                data_local = datetime.now() - timedelta(hours=3)

                # Atualiza preço de venda
                base.sale_price = preco_base
                receptor.sale_price = preco_receptor
                oliva.sale_price = preco_oliva

                if carregador:
                    carregador.sale_price = preco_carregador

                # Registro da montagem (histórico de formação de preço)
                new_assembly = ProductAssembly(
                    store_id=store_id,
                    parent_product_id=base.id,
                    base_unit_id=base.id,
                    receptor_id=receptor.id,
                    oliva_id=oliva.id,
                    carregador_id=carregador.id if carregador else None,
                    quantity=qty,
                    sale_price=Decimal(str(int(final_price))),
                    selling_price_base=Decimal(str(preco_base)),
                    selling_price_receptor=Decimal(str(preco_receptor)),
                    selling_price_oliva=Decimal(str(preco_oliva)),
                    selling_price_carregador=Decimal(str(preco_carregador)) if carregador else None,
                    status='CONCLUIDO',
                    assembly_date=data_local
                )

                db.session.add(new_assembly)
                db.session.commit()

                flash(
                    f'Preço gerado com sucesso! '
                    f'Base R$ {preco_base}, '
                    f'Receptor R$ {preco_receptor}, '
                    f'Oliva R$ {preco_oliva}'
                    f'{f", Carregador R$ {preco_carregador}" if carregador else ""}. '
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
        rateio_carregador=rateio_carregador,
        carregador_selecionado=carregador_selecionado,
    )