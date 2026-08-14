from flask import Blueprint, session, render_template, redirect, url_for, flash, request, jsonify, send_file
from admin.quote.models import Quote, QuoteItem, PaymentInstallmentCondition, db
from admin.client.models import Client
from admin.models import Product, Store
from admin.assembly.models import ProductAssembly
import base64, os, logging, traceback, re, shutil
import unidecode
from datetime import datetime, timedelta
from sqlalchemy import desc

try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    pdfkit = None
    PDFKIT_AVAILABLE = False

quote_bp = Blueprint('quote_bp', __name__, template_folder='templates')

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# HELPER: sale_price mais atual em product_assembly
# ─────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# HELPER: mapa {installments: coefficient} das condições ativas
# ─────────────────────────────────────────────────────────────
def get_coefficient_map():
    conditions = (
        PaymentInstallmentCondition.query
        .filter_by(active=True)
        .order_by(PaymentInstallmentCondition.installments)
        .all()
    )
    return {c.installments: float(c.coefficient) for c in conditions}


# ─────────────────────────────────────────────────────────────
# API JSON — retorna lista de produtos com sale_price e discount
# Faz JOIN entre product_assembly e product
# Retorna o sale_price mais recente do product_assembly por produto
# ─────────────────────────────────────────────────────────────
@quote_bp.route('/admin/quote/products', methods=['GET'])
def quote_products():
    if 'email' not in session:
        return jsonify({'error': 'Não autenticado'}), 401

    store_id = int(session['Store']['Id'])

    # Subconsulta: pega o assembly mais recente por parent_product_id
    subq = (
        db.session.query(
            ProductAssembly.parent_product_id,
            db.func.max(ProductAssembly.assembly_date).label('max_date')
        )
        .filter(ProductAssembly.store_id == store_id)
        .group_by(ProductAssembly.parent_product_id)
        .subquery()
    )

    # JOIN: product_assembly (mais recente) + product
    rows = (
        db.session.query(
            Product.id,
            Product.name,
            Product.discount,
            ProductAssembly.sale_price
        )
        .join(subq, Product.id == subq.c.parent_product_id)
        .join(
            ProductAssembly,
            db.and_(
                ProductAssembly.parent_product_id == subq.c.parent_product_id,
                ProductAssembly.assembly_date     == subq.c.max_date,
                ProductAssembly.store_id          == store_id
            )
        )
        .filter(Product.store_id == store_id)
        .order_by(Product.name)
        .all()
    )

    result = [
        {
            'id':         r.id,
            'name':       r.name,
            'sale_price': float(r.sale_price or 0),
            'discount':   float(r.discount   or 0),
        }
        for r in rows
    ]
    return jsonify(result)


# ─────────────────────────────────────────────────────────────
# LISTAGEM
# ─────────────────────────────────────────────────────────────
@quote_bp.route('/admin/quote/list')
def quote_list():
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    store_id = int(session['Store']['Id'])
    quotes = (
        Quote.query
        .filter_by(store_id=store_id)
        .order_by(Quote.created_at.desc())
        .all()
    )
    return render_template('quote/quote_list.html', quotes=quotes, titulo='Orçamentos')


# ─────────────────────────────────────────────────────────────
# CRIAÇÃO
# ─────────────────────────────────────────────────────────────
@quote_bp.route('/admin/quote/new', methods=['GET', 'POST'])
def quote_create():
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    store_id = int(session['Store']['Id'])

    clients = (
        Client.query
        .filter_by(store_id=store_id)
        .order_by(Client.name)
        .all()
    )

    default_valid = datetime.now() + timedelta(days=30)

    if request.method == 'POST':
        try:
            client_id    = request.form.get('client_id')
            valid_until  = request.form.get('valid_until')
            observations = request.form.get('observations', '').strip().upper()
            discount     = float(request.form.get('discount') or 0)

            product_ids   = request.form.getlist('product_id[]')
            descriptions  = request.form.getlist('description[]')
            quantities    = request.form.getlist('quantity[]')
            unit_prices   = request.form.getlist('unit_price[]')
            discount_pcts = request.form.getlist('discount_pct[]')

            if not client_id:
                flash('❌ Selecione um cliente.', 'danger')
                return render_template('quote/quote_create.html',
                                       clients=clients,
                                       default_valid=default_valid,
                                       titulo='Novo Orçamento')

            if not product_ids or all(not p for p in product_ids):
                flash('❌ Adicione pelo menos um item.', 'danger')
                return render_template('quote/quote_create.html',
                                       clients=clients,
                                       default_valid=default_valid,
                                       titulo='Novo Orçamento')

            valid_dt = None
            if valid_until:
                try:
                    valid_dt = datetime.strptime(valid_until, '%Y-%m-%d')
                except ValueError:
                    pass

            quote = Quote(
                number=int(datetime.now().strftime('%Y%m%d%H%M%S')),
                store_id=store_id,
                client_id=client_id,
                valid_until=valid_dt,
                observations=observations,
                discount=discount,
                total=0,
                status='PENDENTE'
            )
            db.session.add(quote)
            db.session.flush()

            subtotal = 0

            for i in range(len(product_ids)):
                pid      = product_ids[i]
                desc_txt = descriptions[i].strip().upper() if i < len(descriptions) else ''
                qty      = float(quantities[i])    if i < len(quantities)    else 1
                price    = float(unit_prices[i])   if i < len(unit_prices)   else 0
                disc_pct = float(discount_pcts[i]) if i < len(discount_pcts) else 0

                if not pid or not desc_txt or qty <= 0:
                    continue

                item_total = round(qty * price * (1 - disc_pct / 100), 2)
                subtotal  += item_total

                item = QuoteItem(
                    quote_id=quote.id,
                    product_id=int(pid) if pid else None,
                    description=desc_txt,
                    quantity=qty,
                    unit_price=price,
                    discount_pct=disc_pct,
                    total=item_total
                )
                db.session.add(item)

            quote.total = max(subtotal - discount, 0)
            db.session.commit()
            flash(f'✅ Orçamento nº {quote.number} criado com sucesso!', 'success')
            return redirect(url_for('quote_bp.quote_list'))

        except Exception as e:
            db.session.rollback()
            logger.error(traceback.format_exc())
            flash(f'❌ Erro ao criar orçamento: {e}', 'danger')

    return render_template('quote/quote_create.html',
                           clients=clients,
                           default_valid=default_valid,
                           titulo='Novo Orçamento')


# ─────────────────────────────────────────────────────────────
# VISUALIZAÇÃO / PDF
# ─────────────────────────────────────────────────────────────
@quote_bp.route('/admin/quote/view/<int:quote_id>', methods=['GET', 'POST'])
def quote_view(quote_id):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))


    store        = session['Store']
    store_logo   = store['Logo']
    caminho_logo = 'img/admin/' + store_logo
    store_id     = int(session['Store']['Id'])
    store_obj    = Store.query.get(store_id)

    quote = Quote.query.get_or_404(quote_id)
    items = QuoteItem.query.filter_by(quote_id=quote_id).all()

    try:
        first_name   = quote.client.name.split(' ')[0]
        sanitized    = re.sub(r'[^a-z0-9]', '', unidecode.unidecode(first_name).lower())
        new_filename = f'orcamento-{sanitized}.pdf'
    except Exception:
        new_filename = f'orcamento-{quote.number}.pdf'

    if request.method == 'POST':
        if not PDFKIT_AVAILABLE:
            flash('❌ pdfkit não instalado. Execute: pip install pdfkit', 'danger')
            return redirect(url_for('quote_bp.quote_view', quote_id=quote_id))

        try:
            try:
                with open(f'static/img/admin/{store_logo}', 'rb') as f:
                    logohtml = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')
            except Exception:
                logohtml = ''

            rendered = render_template('quote/quote_pdf.html',
                                       logohtml=logohtml,
                                       quote=quote,
                                       items=items,
                                       store=store,
                                       store_obj=store_obj,
                                       coef_map=get_coefficient_map(),
                                       titulo='Orçamento')

            pdf_folder = 'static/pdf'
            os.makedirs(pdf_folder, exist_ok=True)
            pdf_path = os.path.join(pdf_folder, new_filename)

            options = {
                'encoding': 'UTF-8',
                'orientation': 'Portrait',
                'header-center': 'Orçamento',
                'header-right': 'Página: [page]/[toPage]',
                'header-left': store.get('Name', 'Ouvirtiba'),
                'footer-right': 'Emissão: [date]',
                'footer-left': f'Arquivo: {new_filename}',
                'footer-line': '',
                'footer-spacing': 2,
                'enable-local-file-access': '',
                'quiet': ''
            }

            wkhtmltopdf_paths = [
                shutil.which('wkhtmltopdf'),
                '/usr/local/bin/wkhtmltopdf',
                '/usr/bin/wkhtmltopdf',
                r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
                r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
            ]
            config = None
            for path in wkhtmltopdf_paths:
                if path and os.path.exists(path):
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    break

            if config:
                pdfkit.from_string(rendered, pdf_path, configuration=config, options=options)
            else:
                pdfkit.from_string(rendered, pdf_path, options=options)

            flash('✅ PDF gerado com sucesso!', 'success')

        except OSError:
            flash('❌ wkhtmltopdf não encontrado. Instale com: apt-get install wkhtmltopdf', 'danger')
        except Exception as e:
            logger.error(traceback.format_exc())
            flash(f'❌ Erro ao gerar PDF: {e}', 'danger')

        return redirect(url_for('quote_bp.quote_view', quote_id=quote_id))

    pdf_folder  = 'static/pdf'
    pdf_path    = os.path.join(pdf_folder, new_filename)
    pdf_exists  = os.path.exists(pdf_path)
    pdf_url     = url_for('static', filename=f'pdf/{new_filename}') if pdf_exists else None

    installment_conditions = (
        PaymentInstallmentCondition.query
        .filter_by(active=True)
        .order_by(PaymentInstallmentCondition.installments)
        .all()
    )

    return render_template('quote/quote_view.html',
                           quote=quote,
                           items=items,
                           store=store,
                           store_obj=store_obj,
                           caminho_logo=caminho_logo,
                           pdf_url=pdf_url,
                           installment_conditions=installment_conditions,
                           coef_map=get_coefficient_map(),
                           titulo='Visualizar Orçamento')


# ─────────────────────────────────────────────────────────────
# ATUALIZAR STATUS
# ─────────────────────────────────────────────────────────────
@quote_bp.route('/admin/quote/status/<int:quote_id>', methods=['POST'])
def quote_update_status(quote_id):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    novo_status = request.form.get('status', '').upper()
    allowed = ('APROVADO', 'RECUSADO', 'PENDENTE', 'EXPIRADO')
    if novo_status not in allowed:
        flash('❌ Status inválido.', 'danger')
        return redirect(url_for('quote_bp.quote_list'))

    quote = Quote.query.get_or_404(quote_id)
    try:
        quote.status = novo_status
        db.session.commit()
        flash(f'✅ Status atualizado para {novo_status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao atualizar status: {e}', 'danger')

    return redirect(url_for('quote_bp.quote_view', quote_id=quote_id))

# ─────────────────────────────────────────────────────────────
# DOWNLOAD DO PDF
# ─────────────────────────────────────────────────────────────
@quote_bp.route('/admin/quote/download/<int:quote_id>')
def quote_download(quote_id):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    quote = Quote.query.get_or_404(quote_id)
    try:
        first_name   = quote.client.name.split(' ')[0]
        sanitized    = re.sub(r'[^a-z0-9]', '', unidecode.unidecode(first_name).lower())
        filename     = f'orcamento-{sanitized}.pdf'
    except Exception:
        filename = f'orcamento-{quote.number}.pdf'

    pdf_path = os.path.join('static', 'pdf', filename)
    if not os.path.exists(pdf_path):
        flash('❌ PDF não encontrado. Gere o PDF primeiro.', 'danger')
        return redirect(url_for('quote_bp.quote_view', quote_id=quote_id))

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ─────────────────────────────────────────────────────────────
# COEFICIENTES DE PARCELAMENTO — CRUD
# (ouvirtiba.payment_installment_condition)
# ─────────────────────────────────────────────────────────────

# LISTAGEM
@quote_bp.route('/admin/quote/coefficients')
def coefficient_list():
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    conditions = (
        PaymentInstallmentCondition.query
        .order_by(PaymentInstallmentCondition.installments)
        .all()
    )
    return render_template('quote/coefficient_list.html',
                           conditions=conditions,
                           titulo='Coeficientes de Parcelamento')


# CRIAÇÃO
@quote_bp.route('/admin/quote/coefficients/new', methods=['GET', 'POST'])
def coefficient_create():
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    if request.method == 'POST':
        description  = request.form.get('description', '').strip().upper()
        installments = request.form.get('installments', '').strip()
        coefficient  = request.form.get('coefficient', '').strip().replace(',', '.')

        try:
            installments = int(installments)
            coefficient  = float(coefficient)

            if not description:
                raise ValueError('A descrição é obrigatória.')
            if installments <= 0:
                raise ValueError('O número de parcelas deve ser maior que zero.')
            if coefficient <= 0:
                raise ValueError('O coeficiente deve ser maior que zero.')

            existing = PaymentInstallmentCondition.query.filter_by(
                description=description, installments=installments
            ).first()
            if existing:
                raise ValueError('Já existe uma condição com essa descrição e nº de parcelas.')

            condition = PaymentInstallmentCondition(
                description=description,
                installments=installments,
                coefficient=coefficient,
                active=bool(request.form.get('active'))
            )
            db.session.add(condition)
            db.session.commit()
            flash('✅ Condição de parcelamento criada com sucesso!', 'success')
            return redirect(url_for('quote_bp.coefficient_list'))

        except ValueError as e:
            flash(f'❌ {e}', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.error(traceback.format_exc())
            flash(f'❌ Erro ao criar condição: {e}', 'danger')

        return render_template('quote/coefficient_form.html',
                               condition=None,
                               form_data=request.form,
                               titulo='Nova Condição de Parcelamento')

    return render_template('quote/coefficient_form.html',
                           condition=None,
                           form_data=None,
                           titulo='Nova Condição de Parcelamento')


# EDIÇÃO
@quote_bp.route('/admin/quote/coefficients/edit/<int:condition_id>', methods=['GET', 'POST'])
def coefficient_edit(condition_id):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    condition = PaymentInstallmentCondition.query.get_or_404(condition_id)

    if request.method == 'POST':
        description  = request.form.get('description', '').strip().upper()
        installments = request.form.get('installments', '').strip()
        coefficient  = request.form.get('coefficient', '').strip().replace(',', '.')

        try:
            installments = int(installments)
            coefficient  = float(coefficient)

            if not description:
                raise ValueError('A descrição é obrigatória.')
            if installments <= 0:
                raise ValueError('O número de parcelas deve ser maior que zero.')
            if coefficient <= 0:
                raise ValueError('O coeficiente deve ser maior que zero.')

            existing = PaymentInstallmentCondition.query.filter(
                PaymentInstallmentCondition.description == description,
                PaymentInstallmentCondition.installments == installments,
                PaymentInstallmentCondition.id != condition_id
            ).first()
            if existing:
                raise ValueError('Já existe uma condição com essa descrição e nº de parcelas.')

            condition.description  = description
            condition.installments = installments
            condition.coefficient  = coefficient
            condition.active       = bool(request.form.get('active'))
            db.session.commit()
            flash('✅ Condição de parcelamento atualizada com sucesso!', 'success')
            return redirect(url_for('quote_bp.coefficient_list'))

        except ValueError as e:
            flash(f'❌ {e}', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.error(traceback.format_exc())
            flash(f'❌ Erro ao atualizar condição: {e}', 'danger')

    return render_template('quote/coefficient_form.html',
                           condition=condition,
                           form_data=None,
                           titulo='Editar Condição de Parcelamento')


# ATIVAR / DESATIVAR
@quote_bp.route('/admin/quote/coefficients/toggle/<int:condition_id>', methods=['POST'])
def coefficient_toggle(condition_id):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    condition = PaymentInstallmentCondition.query.get_or_404(condition_id)
    try:
        condition.active = not condition.active
        db.session.commit()
        estado = 'ativada' if condition.active else 'desativada'
        flash(f'✅ Condição {estado} com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(traceback.format_exc())
        flash(f'❌ Erro ao atualizar condição: {e}', 'danger')

    return redirect(url_for('quote_bp.coefficient_list'))


# EXCLUSÃO
@quote_bp.route('/admin/quote/coefficients/delete/<int:condition_id>', methods=['POST'])
def coefficient_delete(condition_id):
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))

    condition = PaymentInstallmentCondition.query.get_or_404(condition_id)
    try:
        db.session.delete(condition)
        db.session.commit()
        flash('✅ Condição de parcelamento excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(traceback.format_exc())
        flash('❌ Não foi possível excluir. Considere desativar a condição em vez de excluir.', 'danger')

    return redirect(url_for('quote_bp.coefficient_list'))