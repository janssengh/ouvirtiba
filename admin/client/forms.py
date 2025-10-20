# admin/client/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, IntegerField, validators
from wtforms.validators import DataRequired, Length, Email, ValidationError

# Importações para validação de documentos e CEP (mantendo a lógica do seu código)
from validate_docbr import CPF, CNPJ
import requests # Necessário para a função validacep
import re # ✅ Importar re para validação de telefone

cpf = CPF()
cnpj = CNPJ()


# =========================================================

def validate_doc_code(form, field):
    """Valida se o campo é um CPF ou CNPJ válido."""
    # Remove caracteres não numéricos para validação
    code_data = ''.join(filter(str.isdigit, field.data))
    
    # ✅ Lógica para tornar o campo obrigatório para FormClientPFJ
    #if form.__class__.__name__ == 'FormClientPFJ' and not code_data:
    #    raise validators.ValidationError('O campo CPF/CNPJ é obrigatório para este tipo de cadastro.')

    if code_data:
        if len(code_data) == 11:
            if not cpf.validate(code_data):
                # ✅ Mensagem de erro personalizada
                raise validators.ValidationError('CPF inválido!')
        elif len(code_data) == 14:
            if not cnpj.validate(code_data):
                # ✅ Mensagem de erro personalizada
                raise validators.ValidationError('CNPJ inválido!')
        else:
            # Permite o campo vazio no FormClientDiv. Se preenchido, deve ser válido.
            if form.__class__.__name__ == 'FormClientPFJ':
                # ✅ Mensagem de erro personalizada
                raise validators.ValidationError('O Código digitado não é um CPF (11 dígitos) nem CNPJ (14 dígitos).')

def validate_phone(form, field):
    """Valida o formato do telefone: Máximo de 11 dígitos (2 DDD + 9 número)."""
    import re # Garante que 're' está disponível
    # Remove caracteres não numéricos
    phone_data = ''.join(filter(str.isdigit, field.data or ''))

    # ✅ CORREÇÃO REGEX: A validação estrita para 11 dígitos (2 DDD + 9 número)
    # ^ : Começo da string
    # \d{11} : Exatamente 11 dígitos numéricos
    # $ : Fim da string
    pattern_11_digits = re.compile(r'^\d{11}$') 
    
    if not phone_data or not pattern_11_digits.match(phone_data):
        # ✅ Mensagem de erro atualizada
        raise validators.ValidationError('Telefone inválido. Deve ter exatamente 11 dígitos numéricos (2 DDD + 9 número).')

def validate_zipcode(form, field):
    """Valida o formato do CEP e consulta a API ViaCEP."""
    cep_data = ''.join(filter(str.isdigit, field.data))
    
    if len(cep_data) != 8:
        raise validators.ValidationError('CEP deve conter 8 dígitos.')
    
    try:
        # Consulta ViaCEP (Melhor mover isso para uma utilidade no servidor)
        response = requests.get(f'https://viacep.com.br/ws/{cep_data}/json/')
        address_data = response.json()
        
        if 'erro' in address_data:
            raise validators.ValidationError('CEP inválido ou não encontrado!')
            
    except requests.exceptions.RequestException:
        # Erro de conexão, mantendo a validação básica
        pass
    

def validate_contact(form, field):
    """Valida se o contato contém apenas números."""
    if not field.data.isdigit():
        raise validators.ValidationError('Contato deve somente conter números!')


# =========================================================
# CLASSES BASE DE FORMULÁRIO
# =========================================================




class BaseClientForm(FlaskForm):
    """Campos comuns para a primeira etapa (Dados Pessoais/Identificação)"""
    name = StringField('Nome / Razão Social', validators=[
        DataRequired('Faltou digitar o nome'),
        Length(min=3, max=50, message="Nome deve ter no mínimo 3 e no máximo 50 caracteres")
    ])
    
    contact = StringField('Telefone de Contato', validators=[
        DataRequired('Faltou digitar o contato'),
        validate_contact
    ])
    
    email = EmailField('E-mail', validators=[
        DataRequired('Faltou digitar o E-mail'),
        Email(message='E-mail inválido'),
        Length(max=50)
    ])


class BaseClientAddressForm(FlaskForm):
    """Campos comuns para a segunda etapa (Endereço)"""
    zipcode = StringField('CEP', validators=[
        DataRequired('Faltou digitar o CEP'),
        validate_zipcode # Validação do CEP via ViaCEP
    ])
    
    address = StringField('Endereço', validators=[
        DataRequired('Faltou digitar o endereço'),
        Length(max=50)
    ])
    
    number = IntegerField('Número', validators=[
        DataRequired('Faltou digitar o número')
    ])
    
    complement = StringField('Complemento', validators=[
        Length(max=45)
    ])
        
    neighborhood = StringField('Bairro', validators=[
        DataRequired('Faltou digitar o bairro'),
        Length(min=3, max=45)
    ])
        
    city = StringField('Cidade', validators=[
        DataRequired('Faltou digitar a cidade'),
        Length(min=3, max=45)
    ])
        
    region = StringField('UF', validators=[
        DataRequired('Faltou digitar a UF'),
        Length(min=2, max=2)
    ])





# =========================================================
# FORMULÁRIOS ESPECÍFICOS DE CADASTRO MULTI-STEP
# =========================================================

class FormClientPFJ(FlaskForm):
    """Formulário 1/2: Cliente Pessoa Física/Jurídica."""
    # code (CPF/CNPJ) é obrigatório e validado pelo validate_doc_code
    # ✅ Adicionando validate_doc_code
    code = StringField('CPF / CNPJ', validators=[validate_doc_code, Length(max=14)])
    
    # ✅ name/razao social é obrigatório
    name = StringField('Nome / Razão Social', validators=[DataRequired('O campo Nome/Razão Social é obrigatório'), Length(max=50)])
    
    # ✅ Telefone com validador customizado
    contact = StringField('Contato', validators=[DataRequired('O campo Contato é obrigatório'), validate_phone]) 
    
    # ✅ E-mail com validador padrão e DataRequired
    email = EmailField('E-mail', validators=[DataRequired('O campo E-mail é obrigatório'), Email('E-mail inválido')])


class FormClientDiv(BaseClientForm):
    """Formulário 1/2: Clientes Diversos (código/contato menos rígido)."""
    code = StringField('Código / Contato', validators=[
        DataRequired('Faltou digitar o Código/Contato'),
        Length(max=14)
        # Note: Não aplicamos validate_doc_code aqui.
    ])
    

class FormClientAddress(BaseClientAddressForm):
    """Formulário 2/2: Endereço (usado em ambos os tipos de cadastro)."""
    # Herda todos os campos de endereço
    pass

# =========================================================
# FORMULÁRIOS ESPECÍFICOS DE EDIÇÃO (Combina Básico + Endereço)
# =========================================================

# Forma mais simples de combinar os campos
class FormClientPFJCompleto(FormClientPFJ, FormClientAddress):
    """Combina campos PF/PJ com todos os campos de Endereço para Edição."""
    # Adiciona o campo 'type' para fins de GET/POST na edição
    type = StringField('Tipo', validators=[validators.Length(min=1, max=1)]) 
    # Hereda code, name, contact, email (FormClientPFJ) e todos os campos de endereço (FormClientAddress)

class FormClientDivCompleto(FormClientDiv, FormClientAddress):
    """Combina campos Diversos com todos os campos de Endereço para Edição."""
    # Adiciona o campo 'type' para fins de GET/POST na edição
    type = StringField('Tipo', validators=[validators.Length(min=1, max=1)]) 
    # Hereda code, name, contact, email (FormClientDiv) e todos os campos de endereço (FormClientAddress)

# Remova o campo 'type' dos Formulários Base se ele for duplicado. Se for usado apenas
# para edição, o código acima está correto.