# admin/blog_post/forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, ValidationError
import re

# =========================================================
# VALIDADORES CUSTOMIZADOS
# =========================================================

def validate_slug(form, field):
    """Valida se o slug contém apenas letras minúsculas, números e hífens."""
    if field.data:
        slug_pattern = re.compile(r'^[a-z0-9-]+$')
        if not slug_pattern.match(field.data):
            raise ValidationError('Slug deve conter apenas letras minúsculas, números e hífens.')

# =========================================================
# FORMULÁRIO DE BLOG POST
# =========================================================

class FormBlogPost(FlaskForm):
    """Formulário completo para criar e editar posts do blog."""
    
    title = StringField('Título', validators=[
        DataRequired('O título é obrigatório'),
        Length(min=5, max=255, message="O título deve ter entre 5 e 255 caracteres")
    ])
    
    summary = TextAreaField('Resumo', validators=[
        DataRequired('O resumo é obrigatório'),
        Length(min=10, max=355, message="O resumo deve ter entre 10 e 355 caracteres")
    ])
    
    content = TextAreaField('Conteúdo', validators=[
        DataRequired('O conteúdo é obrigatório')
        # ✅ SEM Length mínimo: o TinyMCE gera HTML com tags <p>, <img>, etc.
        # que podem ter poucos caracteres de texto visível mas muitos de código HTML
    ])
    
    author = StringField('Autor', validators=[
        DataRequired('O autor é obrigatório'),
        Length(max=45, message="Nome do autor deve ter no máximo 45 caracteres")
    ])
    
    image = FileField('Imagem Destacada', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Apenas imagens são permitidas!')
    ])
    
    slug = StringField('Slug (URL amigável)', validators=[
        Length(max=255, message="O slug deve ter no máximo 255 caracteres"),
        validate_slug
    ])
    
    active = BooleanField('Publicado', default=True)
    
    # Campo oculto para o store_id (preenchido automaticamente)
    store_id = HiddenField()