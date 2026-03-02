# admin/purchases/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField, HiddenField, FieldList, FormField
from wtforms.validators import DataRequired, Length, Regexp, NumberRange, Optional
import re

# =========================================================
# VALIDADORES CUSTOMIZADOS
# =========================================================

def validate_cnpj(form, field):
    """Valida se o CNPJ tem 14 dígitos numéricos."""
    if field.data:
        cnpj = re.sub(r'\D', '', field.data)  # Remove caracteres não numéricos
        if len(cnpj) != 14:
            raise ValidationError('CNPJ deve ter 14 dígitos')
        field.data = cnpj  # Armazena apenas números

# =========================================================
# FORMULÁRIO DE FORNECEDOR
# =========================================================

class FormSupplier(FlaskForm):
    """Formulário para criar e editar fornecedores."""
    
    tax_id = StringField('CNPJ', validators=[
        DataRequired('O CNPJ é obrigatório'),
        Length(min=14, max=18, message="CNPJ inválido")
    ])
    
    corporate_name = StringField('Razão Social', validators=[
        DataRequired('A razão social é obrigatória'),
        Length(min=3, max=40, message="A razão social deve ter entre 3 e 40 caracteres")
    ])
    
    store_id = HiddenField()

# =========================================================
# FORMULÁRIO DE ITEM DA NOTA (SUB-FORMULÁRIO)
# =========================================================

class FormPurchaseInvoiceItem(FlaskForm):
    """Sub-formulário para itens da nota de entrada."""
    
    product_id = SelectField('Produto', coerce=int, validators=[
        DataRequired('Selecione um produto')
    ])
    
    supplier_product_code = StringField('Código do Fornecedor', validators=[
        Optional(),
        Length(max=50, message="Máximo 50 caracteres")
    ])
    
    quantity = DecimalField('Quantidade', validators=[
        DataRequired('Quantidade é obrigatória'),
        NumberRange(min=0.01, message="Quantidade deve ser maior que zero")
    ], places=2)
    
    unit_price = DecimalField('Preço Unitário', validators=[
        DataRequired('Preço unitário é obrigatório'),
        NumberRange(min=0.01, message="Preço deve ser maior que zero")
    ], places=2)

# =========================================================
# FORMULÁRIO DE NOTA DE ENTRADA
# =========================================================

class FormPurchaseInvoice(FlaskForm):
    """Formulário para criar e editar notas de entrada."""
    
    supplier_id = SelectField('Fornecedor', coerce=int, validators=[
        DataRequired('Selecione um fornecedor')
    ])
    
    receipt_date = DateField('Data de Recebimento', validators=[
        DataRequired('Data de recebimento é obrigatória')
    ], format='%Y-%m-%d')
    
    issue_date = DateField('Data de Emissão', validators=[
        DataRequired('Data de emissão é obrigatória')
    ], format='%Y-%m-%d')
    
    entry_exit_date = DateField('Data de Entrada/Saída', validators=[
        DataRequired('Data de entrada/saída é obrigatória')
    ], format='%Y-%m-%d')
    
    invoice_number = StringField('Número da Nota', validators=[
        DataRequired('Número da nota é obrigatório'),
        Length(max=20, message="Máximo 20 caracteres")
    ])
    
    series = StringField('Série', validators=[
        DataRequired('Série é obrigatória'),
        Length(max=10, message="Máximo 10 caracteres")
    ])
    
    total_amount = DecimalField('Valor Total', validators=[
        DataRequired('Valor total é obrigatório'),
        NumberRange(min=0.01, message="Valor deve ser maior que zero")
    ], places=2)
    
    store_id = HiddenField()
    
    # Lista de itens (para adicionar dinamicamente via JavaScript)
    # items = FieldList(FormField(FormPurchaseInvoiceItem), min_entries=1)