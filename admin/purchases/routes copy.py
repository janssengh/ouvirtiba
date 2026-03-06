# admin/purchases/routes.py

from flask import Blueprint, session, render_template, redirect, url_for, flash, request
from datetime import datetime
import re, math

from .models import Supplier, PurchaseInvoice, PurchaseInvoiceItem, db
from .forms import FormSupplier, FormSupplierUpd, FormPurchaseInvoice, FormPurchaseInvoiceItem
from admin.models import Product

purchases_bp = Blueprint('purchases_bp', __name__, template_folder='templates')

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def limpar_cnpj(cnpj):
    """Remove caracteres não numéricos do CNPJ."""
    return re.sub(r'\D', '', cnpj) if cnpj else ''

def formatar_cnpj(cnpj):
    """Formata CNPJ para exibição: 00.000.000/0000-00"""
    if not cnpj or len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"

def exibir_erros_formulario(form):
    """Exibe mensagens flash detalhadas para cada erro de validação."""
    for field_name, errors in form.errors.items():
        field = getattr(form, field_name, None)
        label = field.label.text if field and hasattr(field, 'label') else field_name
        for error in errors:
            flash(f'Campo "{label}": {error}', 'warning')

# =========================================================
# ROTAS CRUD - FORNECEDOR (SUPPLIER)
# =========================================================

@purchases_bp.route('/admin/purchases/supplier/list')
def supplier_list():
    """Lista todos os fornecedores da loja."""
    store_id = session.get('store_id')
    suppliers = Supplier.query.filter_by(store_id=store_id).order_by(Supplier.corporate_name).all()
    return render_template('admin/purchases/supplier_list.html', suppliers=suppliers)


@purchases_bp.route('/admin/purchases/supplier/create', methods=['GET', 'POST'])
def supplier_create():
    """Cria um novo fornecedor."""
    form = FormSupplier()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # Limpa o CNPJ
                cnpj_limpo = limpar_cnpj(form.tax_id.data)
                
                # Verifica se já existe fornecedor com este CNPJ na loja
                existing = Supplier.query.filter_by(
                    store_id=session.get('store_id'),
                    tax_id=cnpj_limpo
                ).first()
                
                if existing:
                    flash(f'Já existe um fornecedor com o CNPJ {formatar_cnpj(cnpj_limpo)} cadastrado.', 'warning')
                    return render_template('admin/purchases/supplier_create.html', form=form, titulo="Novo Fornecedor")
                
                new_supplier = Supplier(
                    store_id=session.get('store_id'),
                    tax_id=cnpj_limpo,
                    corporate_name=form.corporate_name.data.upper(),
                    created_at=datetime.now()
                )
                
                db.session.add(new_supplier)
                db.session.commit()
                
                flash(f'Fornecedor "{new_supplier.corporate_name}" cadastrado com sucesso!', 'success')
                return redirect(url_for('purchases_bp.supplier_list'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar fornecedor: {str(e)}', 'danger')
        else:
            exibir_erros_formulario(form)
    
    return render_template('admin/purchases/supplier_create.html', form=form, titulo="Novo Fornecedor")


@purchases_bp.route('/admin/purchases/supplier/update/<int:id>', methods=['GET', 'POST'])
def supplier_update(id):
    """Atualiza um fornecedor existente."""
    supplier = Supplier.query.get_or_404(id)
    form = FormSupplierUpd()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                supplier.corporate_name = form.corporate_name.data.upper()
                
                db.session.commit()
                flash(f'Fornecedor "{supplier.corporate_name}" atualizado com sucesso!', 'success')
                return redirect(url_for('purchases_bp.supplier_list'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar fornecedor: {str(e)}', 'danger')
        else:
            exibir_erros_formulario(form)
    
    elif request.method == 'GET':
        form.corporate_name.data = supplier.corporate_name
    
    return render_template('admin/purchases/supplier_update.html', form=form, supplier=supplier)


@purchases_bp.route('/admin/purchases/supplier/delete/<int:supplier_id>', methods=['POST'])
def supplier_delete(supplier_id):
    """Exclui um fornecedor."""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    try:
        # Verifica se existem notas vinculadas
        invoices_count = PurchaseInvoice.query.filter_by(supplier_id=supplier_id).count()
        
        if invoices_count > 0:
            flash(f'Não é possível excluir "{supplier.corporate_name}". Existem {invoices_count} nota(s) de entrada vinculada(s).', 'danger')
        else:
            supplier_name = supplier.corporate_name
            db.session.delete(supplier)
            db.session.commit()
            flash(f'Fornecedor "{supplier_name}" excluído com sucesso!', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir fornecedor: {str(e)}', 'danger')
    
    return redirect(url_for('purchases_bp.supplier_list'))

# =========================================================
# ROTAS CRUD - NOTA DE ENTRADA (PURCHASE INVOICE)
# =========================================================

@purchases_bp.route('/admin/purchases/invoice/list')
def invoice_list():
    """Lista todas as notas de entrada da loja."""
    store_id = session.get('store_id')
    invoices = PurchaseInvoice.query.filter_by(store_id=store_id)\
        .order_by(PurchaseInvoice.receipt_date.desc()).all()
    return render_template('admin/purchases/invoice_list.html', invoices=invoices)


@purchases_bp.route('/admin/purchases/invoice/create', methods=['GET', 'POST'])
def invoice_create():
    form = FormPurchaseInvoice()
    # Carrega fornecedores
    form.supplier_id.choices = [(s.id, s.corporate_name) for s in Supplier.query.order_by('corporate_name').all()]

    if form.validate_on_submit():
        # --- VALIDAÇÃO DE DATAS NO BACK-END ---
        issue_date = form.issue_date.data
        receipt_date = form.receipt_date.data
        entry_exit_date = form.entry_exit_date.data
        today = datetime.now().date()

        errors = False
        if issue_date > today:
            flash("A Data de Emissão não pode ser maior que a data de hoje.", "danger")
            errors = True
        if receipt_date < issue_date:
            flash("A Data de Recebimento não pode ser menor que a Data de Emissão.", "danger")
            errors = True
        if entry_exit_date < issue_date:
            flash("A Data de Entrada/Saída não pode ser menor que a Data de Emissão.", "danger")
            errors = True

        if errors:
            return render_template('admin/purchases/invoice_create.html', form=form, titulo="Nova Nota de Entrada")
        # ---------------------------------------

        # Buscamos o nome do fornecedor para salvar no dicionário da sessão
        choices_dict = dict(form.supplier_id.choices)
        supplier_corporate_name = choices_dict.get(form.supplier_id.data)

        # Guardamos os dados do cabeçalho na sessão, sem salvar no DB ainda
        total_amount   = float(form.total_amount.data)
        total_liquid   = float(form.total_liquid.data or total_amount)
        total_discount = round(total_amount - total_liquid, 2)

        if total_liquid > total_amount:
            flash("O Total Líquido não pode ser maior que o Total Bruto.", "danger")
            return render_template('admin/purchases/invoice_create.html', form=form, titulo="Nova Nota de Entrada")

        session['temp_invoice'] = {
            'supplier_id': form.supplier_id.data,
            'supplier_corporate_name': supplier_corporate_name,
            'receipt_date': form.receipt_date.data.strftime('%Y-%m-%d'),
            'issue_date': form.issue_date.data.strftime('%Y-%m-%d'),
            'entry_exit_date': form.entry_exit_date.data.strftime('%Y-%m-%d'),
            'invoice_number': form.invoice_number.data,
            'series': form.series.data,
            'total_amount': total_amount,
            'total_discount': total_discount
        }

        session['temp_items'] = [] # Inicia lista de itens vazia
        return redirect(url_for('purchases_bp.invoice_items'))
            
    return render_template('admin/purchases/invoice_create.html', form=form, titulo="Nova Nota de Entrada")


@purchases_bp.route('/admin/purchases/invoice/items')
def invoice_items():
    # O código aqui busca os dados da session['temp_invoice']
    # e não mais pelo ID do banco de dados.
    invoice = session.get('temp_invoice')
    if not invoice:
        return redirect(url_for('purchases_bp.invoice_create'))

    
    # Recupera a lista da sessão (se não existir, retorna uma lista vazia [])
    items = session.get('temp_items', [])

    # CÁLCULO DA SOMA BRUTA DOS ITENS (usa o valor total informado diretamente)
    total_acumulado = round(sum(item['amount'] for item in items), 2)

    # DESCONTO TOTAL DA NOTA (do mestre)
    total_discount = float(invoice.get('total_discount', 0))

    # TOTAL LÍQUIDO ESPERADO = total bruto - desconto
    total_liquido_esperado = float(invoice['total_amount']) - total_discount

    # DIFERENÇA entre soma bruta dos itens e total bruto informado
    diff = abs(float(invoice['total_amount']) - total_acumulado)

    # RATEIO DO DESCONTO POR ITEM (último item absorve diferença de arredondamento)
    items_com_desconto = []
    desconto_acumulado = 0.0
    for idx, item in enumerate(items):
        eh_ultimo = (idx == len(items) - 1)
        subtotal_bruto = float(item['amount'])
        if total_acumulado > 0 and total_discount > 0:
            if eh_ultimo:
                desconto_item = round(total_discount - desconto_acumulado, 2)
            else:
                desconto_item = round((subtotal_bruto / total_acumulado) * total_discount, 2)
                desconto_acumulado += desconto_item
        else:
            desconto_item = 0.0
        items_com_desconto.append({**item, 'desconto_rateado': desconto_item,
                                   'subtotal_liquido': round(subtotal_bruto - desconto_item, 2)})

    # 1. Instancie o formulário que o template está esperando
    form_item = FormPurchaseInvoiceItem()
    
    # 2. Popule o campo de seleção de produtos com os dados do banco
    form_item.product_id.choices = [
        (p.id, p.name) for p in Product.query.order_by('name').all()
    ]
    
    # 3. Passe o 'form_item' para o template
    return render_template(
        'admin/purchases/invoice_items.html', 
        invoice=invoice, 
        items=items_com_desconto, 
        total_acumulado=total_acumulado,
        total_discount=total_discount,
        total_liquido_esperado=total_liquido_esperado,
        diff=diff,
        form_item=form_item   
    )


@purchases_bp.route('/admin/purchases/invoice/item/add', methods=['POST'])
def invoice_item_add():
    """Adiciona um item à nota fiscal de entrada."""
    form = FormPurchaseInvoiceItem()
    # Carrega os produtos para o SelectField
    form.product_id.choices = [(p.id, p.name) for p in Product.query.order_by('name').all()]
    
    # Em vez de buscar no banco por ID, verificamos se existe uma nota na sessão
    if 'temp_invoice' not in session:
        flash('Sessão expirada ou nota não encontrada.', 'danger')
        return redirect(url_for('purchases_bp.invoice_create'))  
       
    items = session.get('temp_items', [])

    if form.validate_on_submit():
      
        # Adiciona item à lista temporária na sessão
        product_id = int(request.form.get('product_id'))
        product = Product.query.get(product_id)
        
        qty = float(form.quantity.data)
        total_item = float(form.amount.data)
        
        # Cálculo do preço unitário com arredondamento para cima (2 casas)
        # Ex: 182.17 / 120 = 1.518083 -> 1.52
        unit_price = math.ceil((total_item / qty) * 100) / 100

        new_item = {
            'product_id': product_id,
            'product_name': product.name,
            'supplier_product_code': form.supplier_product_code.data,
            'quantity': float(qty),
            'unit_price': float(unit_price),
            'amount': float(total_item)
        }
        items.append(new_item)
        session['temp_items'] = items
        session.modified = True
        flash('Item adicionado com sucesso!', 'success')
            
    return redirect(url_for('purchases_bp.invoice_items'))

@purchases_bp.route('/admin/purchases/invoice/finalize', methods=['POST'])
def invoice_finalize():
    # 1. Recupera os dados das sessões
    invoice_data = session.get('temp_invoice')
    items_data = session.get('temp_items', [])

    if not invoice_data:
        flash('Dados da nota não encontrados na sessão.', 'danger')
        return redirect(url_for('purchases_bp.invoice_create'))

    if not items_data:
        flash('A nota deve ter pelo menos um item para ser gravada.', 'warning')
        return redirect(url_for('purchases_bp.invoice_items'))

    # 2. Validação de segurança: Comparar total bruto da NF com a soma dos itens
    total_itens = round(sum(item['amount'] for item in items_data), 2)
    total_discount = float(invoice_data.get('total_discount', 0))

    if abs(total_itens - invoice_data['total_amount']) > 0.01:
        flash(f'Erro de validação: A soma dos itens (R$ {total_itens:.2f}) não condiz com o total bruto da nota (R$ {invoice_data["total_amount"]:.2f}).', 'danger')
        return redirect(url_for('purchases_bp.invoice_items'))

    try:
        # 3. Criar o objeto Mestre (PurchaseInvoice)
        new_invoice = PurchaseInvoice(
            store_id=session.get('store_id'),
            supplier_id=invoice_data['supplier_id'],
            invoice_number=invoice_data['invoice_number'],
            series=invoice_data['series'],
            total_amount=invoice_data['total_amount'],
            total_discount=total_discount,
            issue_date=datetime.strptime(invoice_data['issue_date'], '%Y-%m-%d'),
            receipt_date=datetime.strptime(invoice_data['receipt_date'], '%Y-%m-%d'),
            entry_exit_date=datetime.strptime(invoice_data.get('entry_exit_date', invoice_data['receipt_date']), '%Y-%m-%d'),
            status='Finalizada'
        )

        db.session.add(new_invoice)
        db.session.flush()

        # 4. Pré-carrega todos os produtos necessários de uma vez (evita queries
        #    dentro do loop que causam autoflush e DuplicatePreparedStatement)
        product_ids = [item['product_id'] for item in items_data]
        produtos_map = {
            p.id: p for p in Product.query.filter(Product.id.in_(product_ids)).all()
        }

        # 5. Criar os itens com desconto rateado proporcionalmente
        # Rateio: desconto_item = (subtotal_item / total_bruto) * total_desconto
        # O último item absorve o centavo de arredondamento
        desconto_rateado_acumulado = 0.0

        for idx, item in enumerate(items_data):
            subtotal_item = item['amount']  # usa o valor total informado
            eh_ultimo = (idx == len(items_data) - 1)

            if total_itens > 0 and total_discount > 0:
                if eh_ultimo:
                    # Último item recebe o resto para fechar sem diferença de centavos
                    item_discount = round(total_discount - desconto_rateado_acumulado, 2)
                else:
                    item_discount = round((subtotal_item / total_itens) * total_discount, 2)
                    desconto_rateado_acumulado += item_discount
            else:
                item_discount = 0.0

            new_item = PurchaseInvoiceItem(
                purchase_invoice_id=new_invoice.id,
                product_id=item['product_id'],
                supplier_product_code=item['supplier_product_code'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                discount=item_discount,
                amount=item['amount']   # valor total bruto do item informado na NF
            )
            db.session.add(new_item)

            # --- ATUALIZAÇÃO DO ESTOQUE (usa o map pré-carregado, sem nova query) ---
            product = produtos_map.get(item['product_id'])
            if product:
                current_stock = product.stock if product.stock else 0
                product.stock = current_stock + item['quantity']

        # 5. Commit Final (Grava tudo ou nada)
        db.session.commit()

        # 6. Limpa as sessões após o sucesso
        session.pop('temp_invoice', None)
        session.pop('temp_items', None)

        flash(f'Nota Fiscal {new_invoice.invoice_number} gravada com sucesso no banco de dados!', 'success')
        return redirect(url_for('purchases_bp.invoice_list'))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro crítico ao gravar no banco de dados: {str(e)}', 'danger')
        return redirect(url_for('purchases_bp.invoice_items'))
    

@purchases_bp.route('/admin/purchases/invoice/item/delete/<int:item_index>', methods=['POST'])
def invoice_item_delete(item_index):
    # 1. Recupera a lista de itens da sessão
    items = session.get('temp_items', [])
    
    try:
        # 2. Remove o item da lista pela posição (índice)
        if 0 <= item_index < len(items):
            removed_item = items.pop(item_index)
            session['temp_items'] = items
            session.modified = True
            flash(f"Item {removed_item['product_name']} removido.", "info")
        else:
            flash("Item não encontrado.", "warning")
            
    except Exception as e:
        flash(f"Erro ao remover item: {str(e)}", "danger")
        
    return redirect(url_for('purchases_bp.invoice_items'))

@purchases_bp.route('/admin/purchases/invoice/view/<int:invoice_id>')
def invoice_view(invoice_id):
    """Exibe os detalhes de uma nota fiscal já gravada (somente leitura)."""
    # Busca a nota ou retorna 404 se não existir
    invoice = PurchaseInvoice.query.get_or_404(invoice_id)
    
    return render_template('admin/purchases/invoice_view.html', invoice=invoice)

@purchases_bp.route('/admin/purchases/invoice/delete/<int:invoice_id>', methods=['POST'])
def invoice_delete(invoice_id):
    """Exclui uma nota de entrada e seus itens (cascade)."""
    invoice = PurchaseInvoice.query.get_or_404(invoice_id)
    
    try:
        invoice_number = f"{invoice.invoice_number}/{invoice.series}"

        # Estornar o estoque de cada item antes de excluir
        for item in invoice.items:
            product = Product.query.get(item.product_id)
            if product:
                # Subtraímos a quantidade que havia entrado pela nota
                # Tratamos None como 0 para evitar erros de cálculo
                current_stock = product.stock if product.stock else 0
                product.stock = current_stock - item.quantity
                
                # Opcional: Impedir que o estoque fique negativo (regra de negócio)
                # if product.stock < 0:
                #     product.stock = 0


        db.session.delete(invoice)
        db.session.commit()
        flash(f'Nota de Entrada NF {invoice_number} excluída com sucesso!', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir nota: {str(e)}', 'danger')
    
    return redirect(url_for('purchases_bp.invoice_list'))