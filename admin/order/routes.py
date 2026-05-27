from flask import Blueprint, session, render_template, redirect, url_for, flash, request, make_response
from admin.order.models import Customer_request, Customer_request_item, db
from admin.client.models import Client
from admin.models import Product
import base64, pdfkit.pdfkit, re, unidecode, os
from datetime import datetime

order_bp = Blueprint('order_bp', __name__, template_folder='templates')


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

# Rótulos legíveis para cada tipo de documento
DOC_LABELS = {
    'PED': 'Pedido de Venda',
    'TEG': 'Termo de Entrega em Garantia',
    'OVG': 'O.S. c/ Garantia de Venda',
}

# Título que aparece no PDF / cabeçalho impresso
PDF_TITLES = {
    'PED': 'Pedido de Compra',
    'TEG': 'Termo de Entrega em Garantia',
    'OVG': 'Ordem de Serviço – Garantia de Venda',
}

# Prefixo usado no nome do arquivo PDF salvo
PDF_PREFIX = {
    'PED': 'pedido',
    'TEG': 'teg',
    'OVG': 'ovg',
}

# Rótulo do número no documento impresso
NUM_LABEL = {
    'PED': 'Número Pedido',
    'TEG': 'Número TEG',
    'OVG': 'Número O.S.',
}

OBS_GARANTIA = (
    "A garantia é válida para não funcionamento de fábrica e não cobre "
    "uso inadequado do aparelho, excesso de umidade, excesso de cerumin, "
    "molhado e quebrado, assim como danos aos acessórios (receptores e olivas)."
)


# ──────────────────────────────────────────────────────────────────────────────
# Lista de O.S. / Termos / Pedidos
# ──────────────────────────────────────────────────────────────────────────────

@order_bp.route('/admin/order/list')
def order_list():
    orders = Customer_request.query.order_by(Customer_request.created_at.desc()).all()
    return render_template(
        'admin/order/order_list.html',
        orders=orders,
        titulo="Termos / Ordens de Serviço",
        doc_labels=DOC_LABELS,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Lista de itens de uma O.S.
# ──────────────────────────────────────────────────────────────────────────────

@order_bp.route('/admin/order/<int:order_id>/items')
def orderitem_list(order_id):
    order = Customer_request.query.get_or_404(order_id)
    ordersitem = (
        Customer_request_item.query
        .filter_by(customer_request_id=order_id)
        .order_by(Customer_request_item.price.desc())
        .all()
    )
    return render_template(
        'order/orderitem_list.html',
        order=order,
        ordersitem=ordersitem,
        titulo="Itens da O.S. / Termo",
        doc_labels=DOC_LABELS,
        num_label=NUM_LABEL,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Excluir O.S. / Termo
# ──────────────────────────────────────────────────────────────────────────────

@order_bp.route('/admin/order/delete/<int:order_id>', methods=['POST'])
def order_delete(order_id):
    order = Customer_request.query.get_or_404(order_id)

    if order.status != "N":
        flash("❌ Este documento já foi emitido e não pode ser excluído.", "warning")
        return redirect(url_for('order_bp.order_list'))

    for item in order.items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock += item.quantity
            db.session.add(product)

    try:
        db.session.delete(order)
        db.session.commit()
        flash(f"✅ Documento nº {order.number} excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro ao excluir: {e}", "danger")

    return redirect(url_for('order_bp.order_list'))


# ──────────────────────────────────────────────────────────────────────────────
# Visualizar / Gerar PDF
# ──────────────────────────────────────────────────────────────────────────────

@order_bp.route('/admin/order/orderpdf/<int:order_id>', methods=['GET', 'POST'])
def orderpdf(order_id):
    import logging, traceback

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    try:
        store_logo   = session['Store']['Logo']
        caminho_logo = 'img/admin/' + store_logo
        store        = session['Store']

        order      = Customer_request.query.get_or_404(order_id)
        ordersitem = (
            Customer_request_item.query
            .filter_by(customer_request_id=order_id)
            .order_by(Customer_request_item.price.desc())
            .all()
        )

        doc_type    = order.doc_type or 'PED'
        pdf_titulo  = PDF_TITLES.get(doc_type, 'Pedido de Compra')
        num_lbl     = NUM_LABEL.get(doc_type, 'Número')
        prefix      = PDF_PREFIX.get(doc_type, 'pedido')

        order_number = order.number
        order_status = order.status

        try:
            first_name     = order.client.name.split(' ')[0]
            sanitized_name = re.sub(r'[^a-z0-9]', '', unidecode.unidecode(first_name).lower())
            new_filename   = f'{prefix}-{sanitized_name}.pdf'
            nomearquivo    = f'Arquivo: {new_filename}'
        except Exception:
            new_filename = f'{prefix}-{order_number}.pdf'
            nomearquivo  = f'Arquivo: {new_filename}'

        if request.method == "POST":
            logger.info(f"Gerando PDF para documento {order_number}")

            if order_status == "N":
                order.status = 'S'
                db.session.commit()

            nomearquivo = f'Arquivo: {prefix}-{order_number}.pdf'

            try:
                with open("static/img/admin/" + store_logo, "rb") as img:
                    logo_string = base64.b64encode(img.read()).decode("utf-8")
                logohtml = f'data:image/png;base64,{logo_string}'
            except FileNotFoundError:
                logohtml = ""
                flash("⚠️ Logo não encontrada.", "warning")
            except Exception as e:
                logohtml = ""
                logger.error(f"Erro logo: {e}")

            try:
                rendered = render_template(
                    'order/order_pdf.html',
                    logohtml=logohtml,
                    titulo=pdf_titulo,
                    ordersitem=ordersitem,
                    order=order,
                    store=store,
                    num_label=num_lbl,
                    doc_type=doc_type,
                )
            except Exception as e:
                logger.error(traceback.format_exc())
                flash(f"❌ Erro ao renderizar template: {e}", "danger")
                if order.status == 'S':
                    order.status = 'N'
                    db.session.commit()
                return redirect(url_for('order_bp.order_list'))

            pdf_folder = 'static/pdf'
            os.makedirs(pdf_folder, exist_ok=True)
            pdf_path = os.path.join(pdf_folder, new_filename)

            config = None
            for path in ['/usr/local/bin/wkhtmltopdf', '/usr/bin/wkhtmltopdf',
                         r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe', None]:
                try:
                    if path and os.path.exists(path):
                        config = pdfkit.configuration(wkhtmltopdf=path)
                        break
                    elif path is None:
                        break
                except Exception:
                    continue

            options = {
                'encoding': 'UTF-8',
                'orientation': 'Portrait',
                'header-center': pdf_titulo,
                'header-right': 'Page: [page]/[toPage]',
                'header-left': 'Ouvirtiba Aparelhos Auditivos',
                'footer-right': 'Emissão: [date]',
                'footer-left': nomearquivo,
                'footer-line': '',
                'footer-spacing': 2,
                'enable-local-file-access': '',
                'quiet': '',
            }

            try:
                if config:
                    pdfkit.from_string(rendered, pdf_path, configuration=config, options=options)
                else:
                    pdfkit.from_string(rendered, pdf_path, options=options)
                flash(f"✅ Documento {new_filename} emitido com sucesso!", "success")
            except OSError:
                flash("❌ wkhtmltopdf não encontrado. Instale com: apt-get install wkhtmltopdf", "danger")
                if order.status == 'S':
                    order.status = 'N'
                    db.session.commit()
                return redirect(url_for('order_bp.order_list'))
            except Exception as e:
                logger.error(traceback.format_exc())
                flash(f"❌ Erro ao gerar PDF: {e}", "danger")
                if order.status == 'S':
                    order.status = 'N'
                    db.session.commit()
                return redirect(url_for('order_bp.order_list'))

            return redirect(url_for('order_bp.order_list'))

        # ── GET: visualizar antes de imprimir ──
        return render_template(
            'order/order_pdf.html',
            titulo='Visualizar Documento',
            ordersitem=ordersitem,
            order=order,
            caminho_logo=caminho_logo,
            store=store,
            num_label=num_lbl,
            doc_type=doc_type,
            url_retorno=url_for('order_bp.order_list'),
        )

    except Exception as e:
        import traceback
        flash(f"❌ Erro inesperado: {e}", "danger")
        return redirect(url_for('order_bp.order_list'))


# ──────────────────────────────────────────────────────────────────────────────
# Verificar estoque (AJAX)
# ──────────────────────────────────────────────────────────────────────────────

@order_bp.route('/admin/order/check_stock/<int:product_id>', methods=['GET'])
def check_stock(product_id):
    product = Product.query.get(product_id)
    if not product:
        return {"error": "Produto não encontrado"}, 404
    return {"stock": product.stock}


# ──────────────────────────────────────────────────────────────────────────────
# Criar novo documento (PED / TEG / OVG)
# ──────────────────────────────────────────────────────────────────────────────

@order_bp.route('/admin/order/new', methods=['GET', 'POST'])
def order_create():
    clients  = Client.query.order_by(Client.name).all()
    products = Product.query.filter(
        Product.stock > 0,
        Product.type_id > 0
    ).order_by(Product.name.asc()).all()

    if request.method == 'POST':
        try:
            store_id  = session['store_id']
            client_id = request.form.get('client_id')

            # ── Tipo de documento ────────────────────────────────────────────
            doc_type = request.form.get('doc_type', 'PED')
            if doc_type not in ('PED', 'TEG', 'OVG'):
                flash("Tipo de documento inválido.", "danger")
                return redirect(url_for('order_bp.order_create'))

            # ── Data de emissão ──────────────────────────────────────────────
            issued_at_str = request.form.get('issued_at', '').strip()
            if issued_at_str:
                try:
                    issued_at = datetime.strptime(issued_at_str, '%Y-%m-%d')
                except ValueError:
                    flash("Data de emissão inválida.", "danger")
                    return redirect(url_for('order_bp.order_create'))
            else:
                issued_at = datetime.now()

            # ── Nº NF Fornecedor (somente TEG) ──────────────────────────────
            supplier_invoice = None
            if doc_type == 'TEG':
                supplier_invoice = request.form.get('supplier_invoice', '').strip() or None

            # ── Itens ────────────────────────────────────────────────────────
            product_ids     = request.form.getlist('product_id[]')
            quantities      = request.form.getlist('quantity[]')
            prices          = request.form.getlist('price[]')
            serialnumbers   = request.form.getlist('serialnumber[]')
            discount_values = request.form.getlist('discount_value[]')

            # ── Observação (fixa + complemento) ─────────────────────────────
            obs_form         = request.form.get('observation', '')
            observation_final = f"{OBS_GARANTIA}\n\n{obs_form}" if obs_form.strip() else OBS_GARANTIA

            # ── Pagamento ────────────────────────────────────────────────────
            # TEG: pagamento fixo como "Em Garantia" (código 0)
            if doc_type == 'TEG':
                payment_form      = 0   # 0 = Em Garantia
                payment_condition = 0
                payment_amount_inp = 0.0
                payment_form_inp  = 0
            else:
                payment_form = int(request.form.get('payment_form', 0))
                payment_amount_inp = 0.0
                payment_form_inp   = 0
                payment_condition  = 0

                if payment_form > 3:
                    if payment_form == 4:
                        payment_condition = int(request.form.get('payment_condition', 0))
                        if not 2 <= payment_condition <= 18:
                            flash("Parcelamento inválido (permitido 2 a 18 vezes).", "danger")
                            return redirect(url_for('order_bp.order_create'))
                        payment_amount_inp = 0
                        payment_form_inp   = 0
                    else:
                        payment_amount_inp = float(request.form.get('payment_amount_inp', 0))
                        if payment_amount_inp <= 0:
                            flash("Informe o valor de entrada.", "danger")
                            return redirect(url_for('order_bp.order_create'))
                        payment_form_inp = int(request.form.get('payment_form_inp', 0))
                        if payment_form_inp not in [1, 2, 3]:
                            flash("Selecione a forma de pagamento da entrada.", "danger")
                            return redirect(url_for('order_bp.order_create'))
                        payment_condition = int(request.form.get('payment_condition', 0))
                        if not 1 <= payment_condition <= 18:
                            flash("Parcelamento inválido (permitido 1 a 18 vezes).", "danger")
                            return redirect(url_for('order_bp.order_create'))
                else:
                    payment_condition  = 0
                    payment_amount_inp = 0.0
                    payment_form_inp   = 0

            # ── Cria o registro ──────────────────────────────────────────────
            order = Customer_request(
                store_id=session['Store']['Id'],
                number=int(datetime.now().strftime('%Y%m%d%H%M%S')),
                doc_type=doc_type,
                client_id=client_id,
                issued_at=issued_at,
                supplier_invoice=supplier_invoice,
                observation=observation_final,
                payment_form=payment_form,
                payment_condition=payment_condition,
                payment_amount_inp=payment_amount_inp,
                payment_form_inp=payment_form_inp,
                amount=0,
                status='N',
            )

            db.session.add(order)
            db.session.flush()

            total_pedido   = 0
            total_desconto = 0

            for i in range(len(product_ids)):
                pid        = product_ids[i]
                qty        = quantities[i]      if i < len(quantities)      else None
                prc        = prices[i]          if i < len(prices)          else None
                serial     = serialnumbers[i]   if i < len(serialnumbers)   else None
                disc_value = float(discount_values[i]) if i < len(discount_values) else 0

                if not pid or not qty or not prc:
                    continue

                qty = int(qty)
                product = Product.query.get(pid)
                if not product:
                    continue

                if qty > product.stock:
                    flash(
                        f"❌ Estoque insuficiente para '{product.name}'. "
                        f"Disponível: {product.stock}, solicitado: {qty}.",
                        "danger",
                    )
                    db.session.rollback()
                    return redirect(url_for('order_bp.order_create'))

                preco_original = float(product.sale_price)
                amount_initial = preco_original * qty

                # TEG: preço = 0, desconto = 0 (saída sem cobrança)
                if doc_type == 'TEG':
                    preco_original = 0.0
                    amount_initial = 0.0
                    discount       = 0.0
                    amount         = 0.0
                else:
                    discount = max(0, min(disc_value, amount_initial))
                    amount   = amount_initial - discount

                total_pedido   += amount
                total_desconto += discount

                serial_clean = serial.strip()[:15] if serial and serial.strip() else None

                item = Customer_request_item(
                    customer_request_id=order.id,
                    product_id=pid,
                    quantity=qty,
                    price=preco_original,
                    discount=discount,
                    amount_initial=amount_initial,
                    amount=amount,
                    serialnumber=serial_clean,
                )
                db.session.add(item)

                # ── Baixa de estoque (igual para os 3 tipos) ─────────────────
                product.stock -= qty
                if product.stock < 0:
                    product.stock = 0
                db.session.add(product)

            order.amount   = total_pedido
            order.discount = total_desconto
            db.session.commit()

            label = DOC_LABELS.get(doc_type, 'Documento')
            flash(f"✅ {label} criado com sucesso!", "success")
            return redirect(url_for('order_bp.order_list'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erro ao criar o documento: {str(e)}", "danger")

    return render_template(
        'order/order_create.html',
        clients=clients,
        products=products,
        titulo="Novo Termo / O.S.",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Lista de PDFs gerados
# ──────────────────────────────────────────────────────────────────────────────

@order_bp.route('/admin/order/pdf/list')
def pdf_list():
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    pdf_folder = 'static/pdf'
    pdf_files  = []

    if os.path.exists(pdf_folder):
        for filename in os.listdir(pdf_folder):
            if filename.endswith('.pdf'):
                filepath   = os.path.join(pdf_folder, filename)
                file_stats = os.stat(filepath)
                file_size  = file_stats.st_size

                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"

                created_str = datetime.fromtimestamp(file_stats.st_mtime).strftime('%d/%m/%Y %H:%M')
                pdf_files.append({
                    'name': filename,
                    'size': size_str,
                    'created_at': created_str,
                    'timestamp': file_stats.st_mtime,
                })

        pdf_files.sort(key=lambda x: x['timestamp'], reverse=True)

    return render_template('order/pdf_list.html', pdf_files=pdf_files, titulo="Lista de PDFs Gerados")


@order_bp.route('/admin/order/pdf/delete/<filename>', methods=['POST'])
def pdf_delete(filename):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    if '..' in filename or '/' in filename or '\\' in filename:
        flash("❌ Nome de arquivo inválido!", "danger")
        return redirect(url_for('order_bp.pdf_list'))

    pdf_folder = 'static/pdf'
    filepath   = os.path.join(pdf_folder, filename)

    try:
        if os.path.exists(filepath) and filename.endswith('.pdf'):
            os.remove(filepath)
            flash(f"✅ Arquivo '{filename}' excluído com sucesso!", "success")
        else:
            flash(f"❌ Arquivo '{filename}' não encontrado!", "danger")
    except Exception as e:
        flash(f"❌ Erro ao excluir arquivo: {e}", "danger")

    return redirect(url_for('order_bp.pdf_list'))