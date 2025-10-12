from wtforms import Form, StringField, validators, PasswordField, IntegerField, DecimalField, TextAreaField 
from flask_wtf import FlaskForm # ✅ Importe FlaskForm ou Form (se preferir)
from flask_wtf.file import FileAllowed, FileField, FileRequired


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
    
