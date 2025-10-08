from wtforms import Form, StringField, validators, PasswordField


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