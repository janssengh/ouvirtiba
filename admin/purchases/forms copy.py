from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
from validate_docbr import CNPJ
import re

cnpj_validator = CNPJ()

# =========================================================
# VALIDADOR CNPJ REAL
# =========================================================

def validate_tax_id(form, field):
    """Valida se o campo contém um CNPJ válido."""
    if not field.data:
        raise ValidationError('O CNPJ é obrigatório.')

    cleaned = re.sub(r'\D', '', field.data)

    if len(cleaned) != 14:
        raise ValidationError('CNPJ deve conter 14 dígitos.')

    if not cnpj_validator.validate(cleaned):
        raise ValidationError('CNPJ inválido.')

    field.data = cleaned  # salva apenas números


# =========================================================
# FORMULÁRIO FORNECEDOR
# =========================================================

class FormSupplier(FlaskForm):

    tax_id = StringField('CNPJ', validators=[
        DataRequired('O CNPJ é obrigatório'),
        validate_tax_id
    ])

    corporate_name = StringField('Razão Social', validators=[
        DataRequired('A razão social é obrigatória'),
        Length(min=3, max=50, message="Deve ter entre 3 e 40 caracteres")
    ])

    store_id = HiddenField()


class FormSupplierUpd(FlaskForm):

    corporate_name = StringField('Razão Social', validators=[
        DataRequired('A razão social é obrigatória'),
        Length(min=3, max=50, message="Deve ter entre 3 e 40 caracteres")
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
    
    total_amount = DecimalField('Total Bruto dos Produtos', validators=[
        DataRequired('Valor total bruto é obrigatório'),
        NumberRange(min=0.01, message="Valor deve ser maior que zero")
    ], places=2)

    # Usuário informa o total líquido (NF já com desconto aplicado)
    # O total_discount é derivado no backend: total_amount - total_liquid
    total_liquid = DecimalField('Total Líquido', validators=[
        Optional(),
        NumberRange(min=0, message="Total líquido não pode ser negativo")
    ], places=2, default=0)
    
    store_id = HiddenField()


# =========================================================
# FORMULÁRIO DE ITEM DA NOTA
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