from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class FormProductAssembly(FlaskForm):
    parent_product_id = SelectField('Produto Final (Venda)', coerce=int, validators=[DataRequired()])
    base_unit_id = SelectField('Aparelho Auditivo (Base)', coerce=int, validators=[DataRequired()])
    receptor_id = SelectField('Receptor', coerce=int, validators=[DataRequired()])
    oliva_id = SelectField('Oliva', coerce=int, validators=[DataRequired()])
    carregador_id = SelectField('Carregador (Opcional)', coerce=int, validators=[Optional()])
    quantity = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Finalizar Montagem')


# ✅ NOVO FORM (CLONE)
class FormAssemblyClone(FlaskForm):
    receptor_id = SelectField('Receptor', coerce=int, validators=[DataRequired()])
    oliva_id = SelectField('Oliva', coerce=int, validators=[DataRequired()])
    carregador_id = SelectField('Carregador (Opcional)', coerce=int, validators=[Optional()])

    submit = SubmitField('Gerar Nova Venda')