from flask import Blueprint, render_template, session, flash, url_for, redirect, request
from .models import Product, Store, User
from .forms import LoginFormulario, RegistrationForm
from extension import db, bcrypt  # ✅ importa do módulo central

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')
auth_bp = Blueprint('auth', __name__)

# ---------------- ADMIN ----------------
@admin_bp.route('/')
def product_list():
    if 'email' not in session:
        flash(f'Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    store_logo = session['Store']['Logo']
    url_logo = session['Store']['Url logo']

    produtos = Product.query.filter(Product.store_id == store_id).order_by(
        Product.type_id.asc(),
        Product.name.asc(),
        Product.stock.desc()
    )

    return render_template('admin/product_list.html', titulo='Produtos/Acessórios', produtos=produtos)


def parametrosloja():
    store_id = session['store_id']
    stores = Store.query.filter_by(id=store_id).first()

    if stores:
        urllogo = 'img/admin/' + stores.logo
        urllogowhite = 'img/admin/' + stores.logo_white
        session['Store'] = {
            'Cep origem': stores.zipcode,
            'Taxa frete': stores.freight_rate,
            'Página': stores.pages,
            'Id': stores.id,
            'Name': stores.name,
            'Logo': stores.logo,
            'Address': stores.address,
            'Number': stores.number,
            'Neighborhood': stores.neighborhood,
            'City': stores.city,
            'Region': stores.region,
            'Phone': stores.phone,
            'Complement': stores.complement,
            'Code': stores.code,
            'Url logo': urllogo,
            'Url logo_white': urllogowhite
        }
    return stores


# ---------------- LOGIN ----------------
@auth_bp.route('/login/<origin>', methods=['GET', 'POST'])
def login(origin):
    form = LoginFormulario(request.form)
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            session['Store'] = {'Id': user.store_id}
            if user.store_id is None and user.email != "roeland.e.janssen@gmail.com":
                session['Store'] = {'Id': 0}
                flash(f'Loja não vinculada ao seu login, comunique o administrador!', 'danger')
                return render_template('admin/login.html', form=form, titulo='Login')

            session['email'] = form.email.data
            session['store_id'] = user.store_id
            session['name'] = user.name
            flash(f'{form.email.data} logado com sucesso!', 'success')

            if origin == 'admin':
                return redirect(request.args.get('next') or url_for('admin.product_list'))
            else:
                return redirect(request.args.get('next') or url_for('admin.product_list'))
        else:
            flash('Não foi possível acessar o sistema!', 'danger')
    return render_template('admin/login.html', form=form, titulo='Login')


# ---------------- REGISTRO ----------------
@auth_bp.route('/registrar', methods=['GET', 'POST'])
def registrar():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        hash_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(name=form.name.data, username=form.username.data, email=form.email.data, password=hash_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Obrigado {form.name.data} por registrar!', 'success')
        return redirect(url_for('auth.login', origin='admin'))
    return render_template('admin/registrar.html', form=form, titulo='Registrar')
