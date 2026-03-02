# admin/purchases/routes.py

from flask import Blueprint, session, render_template, redirect, url_for, flash, request
from datetime import datetime
import re

from .models import Supplier, PurchaseInvoice, PurchaseInvoiceItem, db
from .forms import FormSupplier, FormSupplierUpd, FormPurchaseInvoice
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
    """Cria uma nova nota de entrada."""
    form = FormPurchaseInvoice()
    
    # Popula select de fornecedores
    store_id = session.get('store_id')
    form.supplier_id.choices = [(0, 'Selecione...')] + [
        (s.id, f"{s.corporate_name} - {formatar_cnpj(s.tax_id)}")
        for s in Supplier.query.filter_by(store_id=store_id).order_by(Supplier.corporate_name).all()
    ]
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # Verifica duplicidade
                existing = PurchaseInvoice.query.filter_by(
                    store_id=store_id,
                    supplier_id=form.supplier_id.data,
                    invoice_number=form.invoice_number.data,
                    series=form.series.data
                ).first()
                
                if existing:
                    flash(f'Já existe uma nota com número {form.invoice_number.data} e série {form.series.data} para este fornecedor.', 'warning')
                    return render_template('admin/purchases/invoice_create.html', form=form, titulo="Nova Nota de Entrada")
                
                new_invoice = PurchaseInvoice(
                    store_id=store_id,
                    supplier_id=form.supplier_id.data,
                    receipt_date=form.receipt_date.data,
                    issue_date=form.issue_date.data,
                    entry_exit_date=form.entry_exit_date.data,
                    invoice_number=form.invoice_number.data,
                    series=form.series.data,
                    total_amount=form.total_amount.data,
                    created_at=datetime.now()
                )
                
                db.session.add(new_invoice)
                db.session.commit()
                
                flash(f'Nota de Entrada NF {new_invoice.invoice_number}/{new_invoice.series} cadastrada com sucesso!', 'success')
                # Redireciona para adicionar itens
                return redirect(url_for('purchases_bp.invoice_items', invoice_id=new_invoice.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar nota: {str(e)}', 'danger')
        else:
            exibir_erros_formulario(form)
    
    return render_template('admin/purchases/invoice_create.html', form=form, titulo="Nova Nota de Entrada")


@purchases_bp.route('/admin/purchases/invoice/update/<int:id>', methods=['GET', 'POST'])
def invoice_update(id):
    """Atualiza uma nota de entrada existente."""
    invoice = PurchaseInvoice.query.get_or_404(id)
    form = FormPurchaseInvoice()
    
    store_id = session.get('store_id')
    form.supplier_id.choices = [
        (s.id, f"{s.corporate_name} - {formatar_cnpj(s.tax_id)}")
        for s in Supplier.query.filter_by(store_id=store_id).order_by(Supplier.corporate_name).all()
    ]
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # Verifica duplicidade excluindo o próprio registro
                existing = PurchaseInvoice.query.filter(
                    PurchaseInvoice.store_id == store_id,
                    PurchaseInvoice.supplier_id == form.supplier_id.data,
                    PurchaseInvoice.invoice_number == form.invoice_number.data,
                    PurchaseInvoice.series == form.series.data,
                    PurchaseInvoice.id != invoice.id
                ).first()
                
                if existing:
                    flash(f'Já existe outra nota com número {form.invoice_number.data} e série {form.series.data}.', 'warning')
                    return render_template('admin/purchases/invoice_update.html', form=form, invoice=invoice)
                
                invoice.supplier_id = form.supplier_id.data
                invoice.receipt_date = form.receipt_date.data
                invoice.issue_date = form.issue_date.data
                invoice.entry_exit_date = form.entry_exit_date.data
                invoice.invoice_number = form.invoice_number.data
                invoice.series = form.series.data
                invoice.total_amount = form.total_amount.data
                
                db.session.commit()
                flash(f'Nota NF {invoice.invoice_number}/{invoice.series} atualizada com sucesso!', 'success')
                return redirect(url_for('purchases_bp.invoice_list'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar nota: {str(e)}', 'danger')
        else:
            exibir_erros_formulario(form)
    
    elif request.method == 'GET':
        form.supplier_id.data = invoice.supplier_id
        form.receipt_date.data = invoice.receipt_date
        form.issue_date.data = invoice.issue_date
        form.entry_exit_date.data = invoice.entry_exit_date
        form.invoice_number.data = invoice.invoice_number
        form.series.data = invoice.series
        form.total_amount.data = invoice.total_amount
    
    return render_template('admin/purchases/invoice_update.html', form=form, invoice=invoice)


@purchases_bp.route('/admin/purchases/invoice/delete/<int:invoice_id>', methods=['POST'])
def invoice_delete(invoice_id):
    """Exclui uma nota de entrada e seus itens (cascade)."""
    invoice = PurchaseInvoice.query.get_or_404(invoice_id)
    
    try:
        invoice_number = f"{invoice.invoice_number}/{invoice.series}"
        db.session.delete(invoice)
        db.session.commit()
        flash(f'Nota de Entrada NF {invoice_number} excluída com sucesso!', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir nota: {str(e)}', 'danger')
    
    return redirect(url_for('purchases_bp.invoice_list'))


@purchases_bp.route('/admin/purchases/invoice/<int:invoice_id>/items')
def invoice_items(invoice_id):
    """Exibe e gerencia os itens de uma nota de entrada."""
    invoice = PurchaseInvoice.query.get_or_404(invoice_id)
    items = PurchaseInvoiceItem.query.filter_by(purchase_invoice_id=invoice_id).all()
    return render_template('admin/purchases/invoice_items.html', invoice=invoice, items=items)