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

    # Se houver um link para o cadastro nesta template, ele DEVE apontar para 'client_bp.client_register_start'
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
    #ordersitem = order.items  # relacionamento com Customer_request_item

    return render_template(
        'order/orderitem_list.html',
        order=order,
        ordersitem=ordersitem,
        titulo="Itens do Pedido"
    )


@order_bp.route('/admin/order/delete/<int:order_id>', methods=['POST'])
def order_delete(order_id):
    order = Customer_request.query.get_or_404(order_id)

    # Verifica se o pedido pode ser excluído
    if order.status != "N":
        flash("❌ Este pedido já foi emitido e não pode ser excluído.", "warning")
        return redirect(url_for('order_bp.order_list'))

    # 🔄 Repor estoque antes da exclusão
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

# Emitir Pedido
@order_bp.route('/admin/order/orderpdf/<int:order_id>', methods=['GET','POST']) # Corrigido para order_id
def orderpdf(order_id): # Corrigido para order_id
    if 'email' not in session:
        flash(f'Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))
    
    store_id = int(session['Store']['Id'])
    store_logo = session['Store']['Logo']
    caminho_logo = 'img/admin/' + store_logo
    store = session['Store']

    # Dados do Item do Pedido
    order = Customer_request.query.get_or_404(order_id)

    #ordersitem = order.items 
    #ordersitem = sorted(ordersitem, key=lambda item: item.price, reverse=True)

    ordersitem = (
        Customer_request_item.query
        .filter_by(customer_request_id=order_id)
        .order_by(Customer_request_item.price.desc())
        .all()
    )

    order_number = order.number
    order_status = order.status

    # ✅ CORREÇÃO/IMPLEMENTAÇÃO: Novo nome do arquivo (pedidopdf-primeironome.pdf)
    try:
        first_name = order.client.name.split(' ')[0]
        # Sanitiza para URL/Nome de arquivo: remove acentos, caracteres especiais e converte para minúsculas
        sanitized_name = unidecode.unidecode(first_name).lower()
        sanitized_name = re.sub(r'[^a-z0-9]', '', sanitized_name) 

        new_filename = f'pedidopdf-{sanitized_name}.pdf'
        nomearquivo = f'Arquivo: {new_filename}'

    except Exception:
        new_filename = f'pedidopdf-{order_number}.pdf'
        nomearquivo = f'Arquivo: {new_filename}'
        
    if request.method == "POST":  
        # Se pedido não emitido
        if order_status == "N":
            # ❌ Correção: 'order_status' é uma string, você precisa atualizar o objeto 'order'.
            # order_status.status = 'S'
            # ✅ Correção:
            order.status = 'S'
            db.session.commit()

        # Emitir pedido em PDF
        titulo = 'Pedido de Compra'
        nomearquivo = 'Arquivo: pedidopdf-'+ str(order_number)+'.pdf'

        # Transformando imagem para Base64  
        try:
            with open("static/img/admin/" + store_logo, "rb") as image2string:  
                logo_binario = base64.b64encode(image2string.read()) 
            logo_string = logo_binario.decode("utf-8")
            logohtml = (f'data:image/png;base64,{logo_string}')
        except FileNotFoundError:
             # Caso a imagem não seja encontrada, use uma string vazia ou um placeholder
            logohtml = "" 
            flash("⚠️ Logo não encontrada no caminho 'static/img/admin/'", "warning")

        # ⚠️ Melhoria: Adicionar o caminho absoluto para o Bootstrap CDN no header do PDF 
        # Isso é crucial para o wkhtmltopdf renderizar corretamente o CSS
        # Inserido no order_pdf.html (cabeçalho)

        options = {'encoding': 'UTF-8', 
                   'orientation': 'Portrait', 
                   'header-center': titulo, 
                   'header-right': 'Page: [page]/[toPage]', 
                   'header-left': 'Ouvirtiba Aparelhos Auditivos', # Melhoria: Usar o nome da loja
                   'footer-right': 'Emissão: [date]', 
                   'footer-left': nomearquivo,
                   'footer-line': '', 
                   'footer-spacing': 2, 
                   # ❌ Correção: 'enable-local-file-access' não deve ter valor 'None' para funcionar, 
                   # ele deve ser omitido ou o parâmetro correto deve ser usado se necessário
                   # para acesso a arquivos locais, que já é o padrão em alguns casos, mas pode falhar
                   'enable-local-file-access': '' # Pode ser necessário, deixar vazio para garantir que o wkhtmltopdf possa acessar recursos locais/CDN.
                   }

        # Melhoria: Adicionado link para a lista de pedidos no template, então 'caminho_logo' não é mais necessário aqui no POST
        rendered = render_template('order/order_pdf.html', 
                                   logohtml=logohtml, 
                                   titulo='Pedido de Compra', 
                                   ordersitem=ordersitem, 
                                   order=order,
                                   store=store)

        config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')

        # ❌ Correção: Adicionar flash de sucesso após emitir
        flash(f"✅ Pedido {new_filename} emitido com sucesso!", "success")

        try:
            pdf = pdfkit.from_string(rendered, configuration=config, options=options)
        except Exception as e:
            flash(f"❌ Erro ao gerar PDF: {e}", "danger")
            # Reverte a alteração de status se a geração do PDF falhar criticamente
            if order.status == 'S':
                 order.status = 'N'
                 db.session.commit()
            return redirect(url_for('order_bp.order_list'))

        # gerar pdf
        response = make_response(pdf)
        response.headers['content-Type'] = 'application/pdf'

        # attached salva na pasta download
        response.headers['content-Disposition'] = f'attachment;filename="{new_filename}"'        
        # abre o arquivo --> response.headers['content-Disposition'] = 'inline;filename='+ 'pedidopdf-' + str(number)+'.pdf'
        return response

    # ❌ Melhoria: No método GET, renderizar o template e dar a opção de gerar o PDF via POST.
    # Corrigir o redirecionamento após a visualização:
    return render_template('order/order_pdf.html', 
                           titulo='Visualizar Pedido', 
                           ordersitem=ordersitem, 
                           order=order, 
                           caminho_logo=caminho_logo,
                           store=store,
                           url_retorno=url_for('order_bp.order_list')) # Adicionado URL de retorno

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

            payment_form = int(request.form.get('payment_form', 0))  # obrigatório
            payment_amount_inp = 0
            payment_form_inp = 0
            payment_condition = 0

            OBS_FIXA = """ESTE PEDIDO É VALIDO COMO GARANTIA! Garantia válida para revisão a cada 4(quatro) meses e não funcionamento de fábrica. 
A garantia não cobre: uso inadequado do aparelho, excesso de umidade, excesso de cerumin, molhado e quebrado, assim como danos aos acessórios(receptores e olivas)."""
            obs_form = request.form.get('observation', '')  # texto de entrada do usuário
            observation_final = f"{OBS_FIXA}\n\n{obs_form}"

            if payment_form > 3:
                if payment_form == 4:
                    # Cartão Crédito → apenas parcelamento de 2 a 18x
                    payment_condition = int(request.form.get('payment_condition', 0))
                    if not 2 <= payment_condition <= 18:
                        flash("Parcelamento inválido (permitido 2 a 18 vezes).", "danger")
                        return redirect(url_for('order_bp.order_create'))
                    payment_amount_inp = 0
                    payment_form_inp = 0
                else:
                    # Entrada + Parcelas Cartão Crédito
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
                # Dinheiro / Pix / Débito
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
                amount=0,  # será calculado após adicionar itens
                status='N'
            )

            db.session.add(order)
            db.session.flush()  # para pegar o ID antes de adicionar os itens

            total_pedido = 0

            for pid, qty, prc in zip(product_ids, quantities, prices):
                if not pid or not qty or not prc:
                    continue

                qty = int(qty)
                prc = float(prc)

                # 🔎 Buscar produto
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

                # 💾 Inserir item do pedido
                item = Customer_request_item(
                    customer_request_id=order.id,
                    product_id=pid,
                    quantity=qty,
                    price=prc,
                    discount=discount,
                    amount_initial=amount_initial,
                    amount=amount
                )
                db.session.add(item)

                # 📦 Atualizar estoque do produto
                product.stock -= qty
                if product.stock < 0:
                    product.stock = 0  # segurança extra

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
