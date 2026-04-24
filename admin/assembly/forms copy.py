from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class FormProductAssembly(FlaskForm):
    parent_product_id = SelectField('Produto Final (Venda)', coerce=int, validators=[DataRequired()])
    base_unit_id = SelectField('Aparelho Auditivo (Base)', coerce=int, validators=[DataRequired()])
    receptor_id = SelectField('Receptor', coerce=int, validators=[DataRequired()])
    oliva_id = SelectField('Oliva', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Finalizar Montagem')