from flask import Blueprint, session, render_template, redirect, url_for, flash, request, jsonify
from admin.receipt.models import Receipt, ReceiptItem, db
from admin.client.models import Client
from admin.models import Product, Category, Store
from admin.assembly.models import ProductAssembly

import base64
import os
import logging
import traceback
import re
import unidecode

from datetime import datetime, date
from sqlalchemy import desc

receipt_bp = Blueprint('receipt_bp', __name__, template_folder='templates')

logger = logging.getLogger(__name__)


# ============================================================
# HELPER — sale_price
# ============================================================
def get_sale_price(product_id, store_id):
    assembly = (
        ProductAssembly.query
        .filter_by(parent_product_id=product_id, store_id=store_id)
        .order_by(desc(ProductAssembly.assembly_date))
        .first()
    )
    if assembly and assembly.sale_price:
        return float(assembly.sale_price)
    product = Product.query.get(product_id)
    return float(product.sale_price) if product else 0.0


# ============================================================
# API — PREÇO
# ============================================================
@receipt_bp.route('/admin/receipt/price/<int:product_id>', methods=['GET'])
def receipt_get_price(product_id):
    if 'email' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    store_id = int(session['Store']['Id'])
    price = get_sale_price(product_id, store_id)
    return jsonify({'sale_price': price})


# ============================================================
# API — PRODUTOS POR CATEGORIA
# ============================================================
@receipt_bp.route('/admin/receipt/products/<int:category_id>', methods=['GET'])
def receipt_products_by_category(category_id):
    if 'email' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    store_id = int(session['Store']['Id'])
    products = (
        Product.query
        .filter(
            Product.store_id == store_id,
            Product.category_id == category_id,
            Product.sale_price > 0
        )
        .order_by(Product.name)
        .all()
    )
    result = [{'id': p.id, 'name': p.name, 'sale_price': float(p.sale_price or 0)} for p in products]
    return jsonify(result)


# ============================================================
# LISTAGEM
# ============================================================
@receipt_bp.route('/admin/receipt/list')
def receipt_list():
    if 'email' not in session:
        flash('Favor fazer login.', 'danger')
        return redirect(url_for('login', origin='admin'))
    store_id = int(session['Store']['Id'])
    receipts = (
        Receipt.query
        .filter_by(store_id=store_id)
        .order_by(Receipt.created_at.desc())
        .all()
    )
    return render_template('receipt/receipt_list.html', receipts=receipts, titulo='Recibos')


# ============================================================
# NOVO RECIBO
# ============================================================
@receipt_bp.route('/admin/receipt/new', methods=['GET', 'POST'])
def receipt_create():
    if 'email' not in session:
        flash('Favor fazer login.', 'danger')
        return redirect(url_for('login', origin='admin'))

    store_id = int(session['Store']['Id'])

    clients = (
        Client.query
        .filter_by(store_id=store_id)
        .order_by(Client.name)
        .all()
    )

    categories = (
        Category.query
        .filter_by(store_id=store_id)
        .order_by(Category.name)
        .all()
    )

    categories_json = [{'id': c.id, 'name': c.name} for c in categories]
    today_iso = date.today().isoformat()

    if request.method == 'POST':
        try:
            client_id      = request.form.get('client_id')
            payment_method = request.form.get('payment_method')
            observations   = request.form.get('observations', '').strip().upper()
            issue_date_str = request.form.get('issue_date')

            if issue_date_str:
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d')
                if issue_date.date() > date.today():
                    flash('A data de emissão não pode ser maior que hoje.', 'danger')
                    return redirect(url_for('receipt_bp.receipt_create'))
            else:
                issue_date = datetime.now()

            product_ids  = request.form.getlist('product_id[]')
            descriptions = request.form.getlist('description[]')
            quantities   = request.form.getlist('quantity[]')
            unit_prices  = request.form.getlist('unit_price[]')

            if not client_id:
                flash('Selecione um cliente.', 'danger')
                return redirect(url_for('receipt_bp.receipt_create'))

            # Status inicial: GERADO (ainda não emitido fisicamente)
            receipt = Receipt(
                number=int(datetime.now().strftime('%Y%m%d%H%M%S')),
                store_id=store_id,
                client_id=client_id,
                issue_date=issue_date,
                payment_method=payment_method,
                observations=observations,
                total=0,
                status='GERADO'
            )
            db.session.add(receipt)
            db.session.flush()

            total_geral = 0
            for i in range(len(product_ids)):
                pid = product_ids[i]
                if not pid:
                    continue
                product_obj = Product.query.get(int(pid))
                desc_item = product_obj.name if product_obj else descriptions[i]
                qty   = float(quantities[i])
                price = float(unit_prices[i])
                subtotal = round(qty * price, 2)
                total_geral += subtotal
                item = ReceiptItem(
                    receipt_id=receipt.id,
                    product_id=int(pid),
                    description=desc_item,
                    quantity=qty,
                    unit_price=price,
                    total=subtotal
                )
                db.session.add(item)

            receipt.total = total_geral
            db.session.commit()

            flash(f'✅ Recibo nº {receipt.number} gerado!', 'success')
            return redirect(url_for('receipt_bp.receipt_list'))

        except Exception as e:
            db.session.rollback()
            logger.error(traceback.format_exc())
            flash(f'Erro ao gerar recibo: {e}', 'danger')

    return render_template(
        'receipt/receipt_create.html',
        clients=clients,
        categories=categories_json,
        today_iso=today_iso,
        titulo='Novo Recibo'
    )


# ============================================================
# VISUALIZAÇÃO + EMISSÃO (Gerar PDF = Emitir)
# ============================================================
@receipt_bp.route('/admin/receipt/view/<int:receipt_id>', methods=['GET', 'POST'])
def receipt_view(receipt_id):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    import pdfkit

    store        = session['Store']
    store_logo   = store['Logo']
    caminho_logo = 'img/admin/' + store_logo
    store_id     = int(session['Store']['Id'])
    store_obj    = Store.query.get(store_id)

    receipt = Receipt.query.get_or_404(receipt_id)
    items   = ReceiptItem.query.filter_by(receipt_id=receipt_id).all()

    try:
        first_name   = receipt.client.name.split(' ')[0]
        sanitized    = re.sub(r'[^a-z0-9]', '', unidecode.unidecode(first_name).lower())
        new_filename = f'recibo-{sanitized}-{receipt.number}.pdf'
    except Exception:
        new_filename = f'recibo-{receipt.number}.pdf'

    pdf_folder   = 'static/pdf'
    pdf_path     = os.path.join(pdf_folder, new_filename)
    pdf_url      = url_for('static', filename=f'pdf/{new_filename}')
    pdf_exists   = os.path.exists(pdf_path)

    if request.method == 'POST':
        action = request.form.get('action', 'emit')

        if action == 'emit' and receipt.status == 'CANCELADO':
            flash('⚠️ Recibo cancelado não pode ser emitido.', 'warning')
            return redirect(url_for('receipt_bp.receipt_view', receipt_id=receipt_id))

        try:
            with open(f'static/img/admin/{store_logo}', 'rb') as f:
                logohtml = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            logohtml = ''

        rendered = render_template(
            'receipt/receipt_pdf.html',
            logohtml=logohtml, receipt=receipt,
            items=items, store=store, store_obj=store_obj,
            titulo='Recibo de Pagamento'
        )

        os.makedirs(pdf_folder, exist_ok=True)

        options = {
            'encoding': 'UTF-8', 'orientation': 'Portrait',
            'header-center': 'Recibo de Pagamento',
            'header-right': 'Página: [page]/[toPage]',
            'header-left': store.get('Name', 'Ouvirtiba'),
            'footer-right': 'Emissão: [date]',
            'footer-left': f'Arquivo: {new_filename}',
            'footer-line': '', 'footer-spacing': 2,
            'enable-local-file-access': '', 'quiet': ''
        }

        wkhtmltopdf_paths = [
            '/usr/local/bin/wkhtmltopdf', '/usr/bin/wkhtmltopdf',
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe', None
        ]
        config = None
        for path in wkhtmltopdf_paths:
            try:
                if path and os.path.exists(path):
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    break
                elif path is None:
                    break
            except Exception:
                continue

        try:
            if config:
                pdfkit.from_string(rendered, pdf_path, configuration=config, options=options)
            else:
                pdfkit.from_string(rendered, pdf_path, options=options)

            # Gerar PDF = Emitir: atualiza status para EMITIDO
            if receipt.status != 'CANCELADO':
                receipt.status = 'EMITIDO'
                db.session.commit()

            flash(f'✅ Recibo nº {receipt.number} emitido! PDF disponível abaixo.', 'success')
            return redirect(url_for('receipt_bp.receipt_view', receipt_id=receipt_id))

        except OSError:
            flash('❌ wkhtmltopdf não encontrado. Instale com: apt-get install wkhtmltopdf', 'danger')
        except Exception as e:
            flash(f'❌ Erro ao gerar PDF: {e}', 'danger')

        return redirect(url_for('receipt_bp.receipt_view', receipt_id=receipt_id))

    return render_template(
        'receipt/receipt_view.html',
        receipt=receipt, items=items, store=store, store_obj=store_obj,
        caminho_logo=caminho_logo,
        pdf_url=pdf_url if pdf_exists else None,
        titulo='Visualizar Recibo'
    )


# ============================================================
# CANCELAR
# ============================================================
@receipt_bp.route('/admin/receipt/cancel/<int:receipt_id>', methods=['POST'])
def receipt_cancel(receipt_id):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    receipt = Receipt.query.get_or_404(receipt_id)
    if receipt.status == 'CANCELADO':
        flash('⚠️ Este recibo já está cancelado.', 'warning')
        return redirect(url_for('receipt_bp.receipt_list'))

    try:
        receipt.status = 'CANCELADO'
        db.session.commit()
        flash(f'✅ Recibo nº {receipt.number} cancelado.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao cancelar: {e}', 'danger')

    return redirect(url_for('receipt_bp.receipt_list'))