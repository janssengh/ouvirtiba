import re

from wtforms import Form, StringField, validators, PasswordField, IntegerField, DecimalField, TextAreaField, BooleanField
from flask_wtf import FlaskForm # ✅ Importe FlaskForm ou Form (se preferir)
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms.validators import DataRequired, Length, NumberRange, Regexp, URL as WTFormURL
from validate_docbr import CNPJ

cnpj = CNPJ()

# Validação Simples de CNPJ (apenas formato de 14 dígitos)
def validate_cnpj_simple(form, field):
    cnpj_number = re.sub(r'[^0-9]', '', field.data)
    if len(cnpj_number) != 14:
        raise validators.ValidationError('CNPJ deve conter 14 dígitos numéricos.')
    
    if not cnpj.validate(cnpj_number):
        # ✅ Mensagem de erro personalizada
        raise validators.ValidationError('CNPJ inválido!')
    # Para uma validação de dígito verificador, seria necessário instalar uma biblioteca (como pycnpj)


class RegistrationForm(Form):
    name = StringField('Nome Completo :', [validators.Length(min=4, max=25)])
    username = StringField('Usuário', [validators.Length(min=4, max=25)])
    email = StringField('E-mail', [validators.Length(min=6, max=35)])
    password = PasswordField('Informe a sua Senha', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Senha e Confirmação não são iguais!')
    ])
    confirm = PasswordField('Informe a sua Senha Novamente')

class LoginFormulario(Form):
    email = StringField('E-mail', [validators.Length(min=6, max=35)])
    password = PasswordField('Informe a sua Senha', [validators.DataRequired()])

class ProductForm(FlaskForm):
    tipoproduto = IntegerField('Tipo Produto',[validators.NumberRange(min=1, max=2, message="Tipo de produto deve ser no mínimo 1 e no máximo 2"),
                                           validators.InputRequired(message="Faltou digitar o tipo de produto")])

    name = StringField('Nome', validators=[validators.Length(min=20, max=80, message="Nome produto deve ter no mínimo 20 e no máximo 80 caracteres"),
                                                  validators.DataRequired('Faltou digitar o nome do produto')
                                                  ])
    price = DecimalField('Preço', validators=[validators.NumberRange(min=1, max=None, message="O preço deve ser no mínimo 1"),
                                                  validators.DataRequired('Faltou digitar o preço do produto')
                                                  ])
    discount = IntegerField('Taxa de Desconto')
    stock = IntegerField('Quantidade Estoque')
    discription = TextAreaField('Descrição', validators=[validators.Length(min=20, max=250, message="Descrição do produto deve ter no mínimo 20 e no máximo 250 caracteres"),
                                                  validators.DataRequired('Faltou digitar a descrição do produto')
                                                  ])
    #colors = TextAreaField('Cor :',[validators.DataRequired()])

    image_1 = FileField('Imagem 1 :', validators=[
                                                  FileAllowed(['jpg', 'png', 'gif', 'jpeg'])])
    image_2 = FileField('Imagem 2 :', validators=[
                                                  FileAllowed(['jpg', 'png', 'gif', 'jpeg'])])
    image_3 = FileField('Imagem 3 :', validators=[
                                                  FileAllowed(['jpg', 'png', 'gif', 'jpeg'])])
    

class StoreForm(FlaskForm):
    # Campos que exigem validação específica:
    name = StringField('Nome', validators=[DataRequired('O nome da loja é obrigatório.')])
    
    # Código -> CNPJ com validação customizada (14 dígitos)
    code = StringField('CNPJ', validators=[
        DataRequired('O CNPJ é obrigatório.'),
        validate_cnpj_simple # Validação simples do formato
    ])

    # Taxa de frete: maior ou igual a zero
    freight_rate = DecimalField('Taxa de Frete', validators=[
        NumberRange(min=0, message='A taxa de frete deve ser maior ou igual a zero.')
    ])
    
    # Qtde de páginas: maior ou igual a zero
    pages = IntegerField('Qtd. Páginas', validators=[
        NumberRange(min=0, message='A quantidade de páginas deve ser maior ou igual a zero.')
    ])
    
    # Telefone: obrigatório, 10 dígitos (DDD + 8 dígitos)
    phone = StringField('Telefone (DDD+9 dígitos)', validators=[
        DataRequired('O telefone é obrigatório.'),
        Length(min=10,max=10, message='O telefone deve ter exatamente 10 dígitos (DDD+8 dígitos).'),
        Regexp(r'^\d{10}$', message='O telefone deve conter apenas 10 números.')
    ])
    
    # URL: obrigatória, iniciando com https://
    url = StringField('URL', validators=[
        DataRequired('A URL é obrigatória.'),
        WTFormURL(message='Formato de URL inválido. Ex: https://www.exemplo.com'),
        Regexp(r'^https://', message='A URL deve obrigatoriamente começar com "https://".')
    ])

    logotipo_1 = FileField('Logotipo Principal', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Somente imagens!')
    ])
    logotipo_2 = FileField('Logotipo Fundo Claro', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Somente imagens!')
    ])
    
    # Outros campos (não precisam de validação complexa além de obrigatório/tipo)
    zipcode = StringField('CEP Origem', validators=[DataRequired('O CEP é obrigatório.')])
    address = StringField('Endereço', validators=[DataRequired('O endereço é obrigatório.')])
    number = IntegerField('Número', validators=[DataRequired('O número é obrigatório.')])
    complement = StringField('Complemento (opcional)')
    neighborhood = StringField('Bairro', validators=[DataRequired('O bairro é obrigatório.')])
    city = StringField('Cidade', validators=[DataRequired('A cidade é obrigatória.')])
    region = StringField('UF', validators=[DataRequired('O estado (UF) é obrigatório.'), Length(min=2, max=2)])
    home = BooleanField('Destaque na Home')
    state_registration = StringField('Inscrição Estadual', validators=[DataRequired('A Inscrição Estadual é obrigatória.'), Length(max=20, message='Inscrição Estadual deve ter no máximo 20 caracteres.')])
    #home = StringField('Destaque na Home') # Será tratado no routes.py ('S' ou 'N')