from flask import Blueprint, session, render_template, redirect, url_for, flash, request, make_response
from admin.order.models import Customer_request, Customer_request_item, db
from admin.client.models import Client  
from admin.models import Product
import base64, pdfkit.pdfkit, re, unidecode
from datetime import datetime

order_bp = Blueprint('order_bp', __name__, template_folder='templates')

@order_bp.route('/admin/order/list')
def order_list():
    orders = Customer_request.query.all()
    return render_template('admin/order/order_list.html', orders=orders, titulo="Lista de Pedidos")

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
        titulo="Itens do Pedido"
    )


@order_bp.route('/admin/order/delete/<int:order_id>', methods=['POST'])
def order_delete(order_id):
    order = Customer_request.query.get_or_404(order_id)

    if order.status != "N":
        flash("❌ Este pedido já foi emitido e não pode ser excluído.", "warning")
        return redirect(url_for('order_bp.order_list'))

    for item in order.items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock += item.quantity
            db.session.add(product)

    try:
        db.session.delete(order)
        db.session.commit()
        flash(f"✅ Pedido nº {order.number} excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro ao excluir pedido: {e}", "danger")

    return redirect(url_for('order_bp.order_list'))


@order_bp.route('/admin/order/orderpdf/<int:order_id>', methods=['GET','POST'])
def orderpdf(order_id):
    if 'email' not in session:
        flash(f'Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))
    
    store_id = int(session['Store']['Id'])
    store_logo = session['Store']['Logo']
    caminho_logo = 'img/admin/' + store_logo
    store = session['Store']

    order = Customer_request.query.get_or_404(order_id)

    ordersitem = (
        Customer_request_item.query
        .filter_by(customer_request_id=order_id)
        .order_by(Customer_request_item.price.desc())
        .all()
    )

    order_number = order.number
    order_status = order.status

    try:
        first_name = order.client.name.split(' ')[0]
        sanitized_name = unidecode.unidecode(first_name).lower()
        sanitized_name = re.sub(r'[^a-z0-9]', '', sanitized_name) 
        new_filename = f'pedidopdf-{sanitized_name}.pdf'
        nomearquivo = f'Arquivo: {new_filename}'
    except Exception:
        new_filename = f'pedidopdf-{order_number}.pdf'
        nomearquivo = f'Arquivo: {new_filename}'
        
    if request.method == "POST":  
        if order_status == "N":
            order.status = 'S'
            db.session.commit()

        titulo = 'Pedido de Compra'
        nomearquivo = 'Arquivo: pedidopdf-'+ str(order_number)+'.pdf'

        try:
            with open("static/img/admin/" + store_logo, "rb") as image2string:  
                logo_binario = base64.b64encode(image2string.read()) 
            logo_string = logo_binario.decode("utf-8")
            logohtml = (f'data:image/png;base64,{logo_string}')
        except FileNotFoundError:
            logohtml = "" 
            flash("⚠️ Logo não encontrada no caminho 'static/img/admin/'", "warning")

        options = {'encoding': 'UTF-8', 
                   'orientation': 'Portrait', 
                   'header-center': titulo, 
                   'header-right': 'Page: [page]/[toPage]', 
                   'header-left': 'Ouvirtiba Aparelhos Auditivos',
                   'footer-right': 'Emissão: [date]', 
                   'footer-left': nomearquivo,
                   'footer-line': '', 
                   'footer-spacing': 2, 
                   'enable-local-file-access': ''
                   }

        rendered = render_template('order/order_pdf.html', 
                                   logohtml=logohtml, 
                                   titulo='Pedido de Compra', 
                                   ordersitem=ordersitem, 
                                   order=order,
                                   store=store)

        config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')

        flash(f"✅ Pedido {new_filename} emitido com sucesso!", "success")

        try:
            pdf = pdfkit.from_string(rendered, configuration=config, options=options)
        except Exception as e:
            flash(f"❌ Erro ao gerar PDF: {e}", "danger")
            if order.status == 'S':
                 order.status = 'N'
                 db.session.commit()
            return redirect(url_for('order_bp.order_list'))

        response = make_response(pdf)
        response.headers['content-Type'] = 'application/pdf'
        response.headers['content-Disposition'] = f'attachment;filename="{new_filename}"'        
        return response

    return render_template('order/order_pdf.html', 
                           titulo='Visualizar Pedido', 
                           ordersitem=ordersitem, 
                           order=order, 
                           caminho_logo=caminho_logo,
                           store=store,
                           url_retorno=url_for('order_bp.order_list'))

@order_bp.route('/admin/order/check_stock/<int:product_id>', methods=['GET'])
def check_stock(product_id):
    product = Product.query.get(product_id)
    if not product:
        return {"error": "Produto não encontrado"}, 404
    return {"stock": product.stock}

@order_bp.route('/admin/order/new', methods=['GET', 'POST'])
def order_create():
    clients = Client.query.order_by(Client.name).all()
    products = Product.query.filter(Product.stock > 0).order_by(Product.type_id.asc(), Product.name.asc()).all()

    if request.method == 'POST':
        try:
            store_id = session['store_id']
            client_id = request.form.get('client_id')
            observation = request.form.get('observation')
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            prices = request.form.getlist('price[]')
            serialnumbers = request.form.getlist('serialnumber[]')  # ✅ Captura a lista

            payment_form = int(request.form.get('payment_form', 0))
            payment_amount_inp = 0
            payment_form_inp = 0
            payment_condition = 0

            OBS_FIXA = """ESTE PEDIDO É VALIDO COMO GARANTIA! Garantia válida para revisão a cada 4(quatro) meses e não funcionamento de fábrica. 
A garantia não cobre: uso inadequado do aparelho, excesso de umidade, excesso de cerumin, molhado e quebrado, assim como danos aos acessórios(receptores e olivas)."""
            obs_form = request.form.get('observation', '')
            observation_final = f"{OBS_FIXA}\n\n{obs_form}"

            if payment_form > 3:
                if payment_form == 4:
                    payment_condition = int(request.form.get('payment_condition', 0))
                    if not 2 <= payment_condition <= 18:
                        flash("Parcelamento inválido (permitido 2 a 18 vezes).", "danger")
                        return redirect(url_for('order_bp.order_create'))
                    payment_amount_inp = 0
                    payment_form_inp = 0
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
                payment_condition = 0
                payment_amount_inp = 0
                payment_form_inp = 0

            order = Customer_request(
                store_id=session['Store']['Id'],
                number=int(datetime.now().strftime('%Y%m%d%H%M%S')),
                client_id=client_id,
                observation=observation_final,
                payment_form=payment_form,
                payment_condition=payment_condition,
                payment_amount_inp=payment_amount_inp,
                payment_form_inp=payment_form_inp,
                amount=0,
                status='N'
            )

            db.session.add(order)
            db.session.flush()

            total_pedido = 0

            # ✅ CORREÇÃO: Itera sobre os índices das listas
            for i in range(len(product_ids)):
                pid = product_ids[i]
                qty = quantities[i] if i < len(quantities) else None
                prc = prices[i] if i < len(prices) else None
                serial = serialnumbers[i] if i < len(serialnumbers) else None

                if not pid or not qty or not prc:
                    continue

                qty = int(qty)
                prc = float(prc)

                # 🔍 Buscar produto
                product = Product.query.get(pid)
                if not product:
                    continue

                # 🚫 Verificar se há estoque suficiente
                if qty > product.stock:
                    flash(f"❌ Estoque insuficiente para o produto '{product.name}'. "
                        f"Disponível: {product.stock}, solicitado: {qty}.", "danger")
                    db.session.rollback()
                    return redirect(url_for('order_bp.order_create'))

                preco_original = float(product.price)

                # 💰 Calcular desconto e valores
                if prc < preco_original:
                    discount = (preco_original - prc) * qty
                    amount_initial = preco_original * qty
                    amount = prc * qty
                else:
                    discount = 0
                    amount_initial = prc * qty
                    amount = prc * qty

                total_pedido += amount

                # ✅ Limita o serial a 15 caracteres e trata string vazia
                serial_clean = None
                if serial and serial.strip():
                    serial_clean = serial.strip()[:15]

                # 💾 Inserir item do pedido
                item = Customer_request_item(
                    customer_request_id=order.id,
                    product_id=pid,
                    quantity=qty,
                    price=prc,
                    discount=discount,
                    amount_initial=amount_initial,
                    amount=amount,
                    serialnumber=serial_clean  # ✅ Passa o serial limpo
                )
                db.session.add(item)

                # 📦 Atualizar estoque do produto
                product.stock -= qty
                if product.stock < 0:
                    product.stock = 0

                db.session.add(product)

            order.amount = total_pedido
            db.session.commit()
            flash("✅ Pedido criado com sucesso!", "success")
            return redirect(url_for('order_bp.order_list'))

        except Exception as e:
            print(f'e: {e}')
            db.session.rollback()
            flash(f"❌ Erro ao criar o pedido: {str(e)}", "danger")

    return render_template(
        'order/order_create.html',
        clients=clients,
        products=products,
        titulo="Novo Pedido"
    )