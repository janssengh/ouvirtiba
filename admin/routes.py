from flask import Blueprint, render_template, session, flash, url_for, redirect, request
from .models import Product, Store, User, Brand, Category, Size, Packaging, Color
from .forms import LoginFormulario, RegistrationForm, ProductForm
from extension import db, bcrypt  # ✅ importa do módulo central
from utils import login_required


import os, secrets
from flask import current_app

# Dicionário auxiliar para mapear o ID do formato para sua descrição
FORMAT_DESCRIPTIONS = {
    1: "Caixa/Pacote",
    2: "Rolo/Prisma",
    3: "Envelope"
}

def get_format_description(format_id):
    """Retorna a descrição do formato baseado no ID."""
    try:
        return FORMAT_DESCRIPTIONS.get(int(format_id), "Formato Desconhecido")
    except (TypeError, ValueError):
        return "Formato Inválido"

def safe_float_conversion(value, field_name):
    """Tenta converter para float e levanta erro se falhar ou for None/vazio."""
    if not value:
        raise ValueError(f'O campo "{field_name}" é obrigatório.')
    try:
        # Tenta converter para float para aceitar números decimais (ex: peso/dimensões)
        return float(value)
    except ValueError:
        raise ValueError(f'O campo "{field_name}" deve ser um número válido.')

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')
auth_bp = Blueprint('auth', __name__)

# ---------------- ADMIN ----------------
@admin_bp.route('/', defaults={'type_id': None})
@admin_bp.route('/<int:type_id>')
@login_required
def product_list(type_id):
    print('entrou na rota admin')
    if 'email' not in session:
        flash(f'Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))
    
    # ✅ CORREÇÃO: Força type_id = 1 se for None
    if type_id is None:
        type_id = 1 
        # Opcional: Redirecionar para /admin/1 para que a URL seja limpa
        # return redirect(url_for('admin.product_list', type_id=1))

    parametrosloja()
    store_id = session['store_id']

    store_logo = session['Store']['Logo']
    url_logo = session['Store']['Url logo']

    # Cria o filtro base (sempre filtra pela loja)
    query = Product.query.filter(Product.store_id == store_id)

    # Se o type_id foi informado (1, 2 etc.), adiciona ao filtro
    if type_id is not None and type_id in [1, 2]: # Garante que só filtra se for 1 ou 2
        query = query.filter(Product.type_id == type_id)

    # Ordena os resultados
    produtos = query.order_by(
        Product.type_id.asc(),
        Product.category_id.asc(),
        Product.name.asc(),
        Product.stock.desc()
    ).all()


    return render_template('admin/product_list.html', produtos=produtos, type_id=type_id)


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
                return redirect(request.args.get('next') or url_for('admin.product_list', type_id=1))
            else:
                return redirect(request.args.get('next') or url_for('admin.product_list', type_id=1))
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

@auth_bp.route('/logout')
def logout():
    session.clear()  # remove todas as variáveis de sessão (email, store_id, etc)
    flash('Você saiu do sistema com sucesso!', 'info')
    return redirect(url_for('auth.login', origin='admin'))

@admin_bp.route('/produto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def produto_editar(id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    produto = Product.query.get_or_404(id)
    parametrosloja()

    form = ProductForm(request.form, obj=produto)

    print("Método:", request.method)
    print("is_submitted:", form.is_submitted())
    print("validate:", form.validate())
    print("Errors:", form.errors)

    if form.validate_on_submit():
        print('✅ Entrou no form.validate')
        campos_alterados = False

        # --- Atualiza relações de chave estrangeira (selects) ---
        for campo_form, campo_model in [
            ('marca', 'brand_id'),
            ('categoria', 'category_id'),
            ('cor', 'color_id'),
            ('tamanho', 'size_id'),
            ('embalagem', 'packaging_id')
        ]:
            novo_valor = int(request.form.get(campo_form, getattr(produto, campo_model)))
            if novo_valor != getattr(produto, campo_model):
                setattr(produto, campo_model, novo_valor)
                campos_alterados = True

        # --- Atualiza o nome da cor (coluna colors) ---
        color_id = int(request.form.get('cor', produto.color_id))
        color = Color.query.get(color_id)
        if color and color.name != produto.colors:
            produto.colors = color.name
            campos_alterados = True

        # --- Atualiza campos simples vindos do formulário ---
        for campo in ['name', 'price', 'discount', 'stock', 'discription']:
            novo_valor = getattr(form, campo).data
            if novo_valor != getattr(produto, campo):
                setattr(produto, campo, novo_valor)
                campos_alterados = True

        # --- Atualização das imagens, se houver upload ---
        upload_dir = os.path.join(current_app.root_path, 'static', 'img', 'admin')
        os.makedirs(upload_dir, exist_ok=True)

        def atualizar_imagem(campo_nome, attr_nome):
            """Atualiza imagem do produto e retorna True se houve alteração"""
            arquivo = request.files.get(campo_nome)
            if arquivo and arquivo.filename:
                imagem_antiga = getattr(produto, attr_nome)
                if imagem_antiga:
                    caminho_antigo = os.path.join(upload_dir, imagem_antiga)
                    if os.path.exists(caminho_antigo):
                        try:
                            os.unlink(caminho_antigo)
                        except Exception as e:
                            print(f"Erro ao excluir imagem antiga {imagem_antiga}: {e}")

                # Gera nome único e salva
                nome_seguro = secrets.token_hex(10) + os.path.splitext(arquivo.filename)[1]
                caminho_novo = os.path.join(upload_dir, nome_seguro)
                arquivo.save(caminho_novo)

                # ✅ Atualiza o nome da imagem no banco
                setattr(produto, attr_nome, nome_seguro)
                print(f'🖼️ Imagem atualizada: {attr_nome} -> {nome_seguro}')
                return True
            return False

        # Verifica se alguma imagem foi trocada
        if atualizar_imagem('image_1', 'image_1'):
            campos_alterados = True
        if atualizar_imagem('image_2', 'image_2'):
            campos_alterados = True
        if atualizar_imagem('image_3', 'image_3'):
            campos_alterados = True

        print(f'campos_alterados: {campos_alterados}')
        if campos_alterados:
            db.session.commit()
            flash(f'O produto "{produto.name}" foi atualizado com sucesso!', 'success')
        else:
            flash('Nenhuma alteração foi feita.', 'info')

        return redirect(url_for('admin.product_list', type_id=produto.type_id))

    print('⚠️ Não entrou no form.validate')

    # --- GET: exibe formulário com dados atuais ---
    marcas = Brand.query.all()
    categorias = Category.query.all()
    cores = Color.query.all()
    tamanhos = Size.query.all()
    embalagens = Packaging.query.all()

    return render_template(
        'admin/product_upd.html',
        form=form,
        produto=produto,
        marcas=marcas,
        categorias=categorias,
        cores=cores,
        tamanhos=tamanhos,
        embalagens=embalagens,
        titulo=f'Editar: {produto.name}'
    )

@admin_bp.route('/produto/inserir', methods=['GET', 'POST'], defaults={'type_id': None}) # Adiciona defaults    )
@admin_bp.route('/produto/inserir/<int:type_id>', methods=['GET', 'POST'])
@login_required
def produto_inserir(type_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    form = ProductForm()

        # Determina o nome do tipo de produto para exibir no template
    tipo_nome = "Aparelhos Auditivos" if type_id == 1 else "Acessórios" if type_id == 2 else "Todos os Produtos"
    # ✅ Preenche o campo 'type_id' do formulário com o valor da URL
    # Isso faz com que o WTForms saiba qual valor deve ser usado na renderização
    if type_id is not None:
        form.tipoproduto.data = type_id 


    # ✅ Se o tipo vier pela URL, pré-seleciona no formulário
    if type_id:
        form.tipoproduto.data = type_id

    # --- GET: renderiza formulário de inserção ---
    marcas = Brand.query.all()
    categorias = Category.query.all()
    cores = Color.query.all()
    tamanhos = Size.query.all()
    embalagens = Packaging.query.all()


    if form.validate_on_submit():
        print("✅ Entrou no form.validate")

        # --- Captura os dados do formulário ---
        type_id = int(request.form.get('tipoproduto'))
        brand_id = int(request.form.get('marca'))
        category_id = int(request.form.get('categoria'))
        color_id = int(request.form.get('cor').split(',')[0])  # o select tem id,name juntos
        size_id = int(request.form.get('tamanho'))
        packaging_id = int(request.form.get('embalagem'))

        # Busca a descrição da cor
        if color_id:
            try:
                # ✅ CORREÇÃO: Tenta converter o valor para inteiro.
                # Se color_id_raw for '1', color_id_int será 1. Se for uma string inválida, 
                # o 'except ValueError' será acionado.
                color_id_int = int(color_id)
                
                # Agora color_id_int é garantidamente um inteiro.
                cor_obj = Color.query.get(color_id_int) 
                
                if cor_obj:
                    color_name = cor_obj.name # Pega o nome da cor
                    
            except ValueError:
                # Se a conversão falhar (valor do form não é um número), ignora ou trata o erro.
                pass
                
        # --- Upload das imagens ---
        upload_dir = os.path.join(current_app.root_path, 'static', 'img', 'admin')
        os.makedirs(upload_dir, exist_ok=True)

        def salvar_imagem(campo_nome):
            arquivo = request.files.get(campo_nome)
            if arquivo and arquivo.filename:
                nome_seguro = secrets.token_hex(10) + os.path.splitext(arquivo.filename)[1]
                caminho = os.path.join(upload_dir, nome_seguro)
                arquivo.save(caminho)
                print(f"🖼️ Imagem salva: {nome_seguro}")
                return nome_seguro
            return 'image.jpg'  # imagem padrão se não enviada

        image_1 = salvar_imagem('image_1')
        image_2 = salvar_imagem('image_2')
        image_3 = salvar_imagem('image_3')

        # --- Cria o novo produto ---
        novo_produto = Product(
            type_id=type_id,
            name=form.name.data,
            price=form.price.data,
            discount=form.discount.data or 0,
            stock=form.stock.data or 0,
            colors=color_name,
            discription=form.discription.data,
            brand_id=brand_id,
            category_id=category_id,
            color_id=color_id,
            size_id=size_id,
            packaging_id=packaging_id,
            image_1=image_1,
            image_2=image_2,
            image_3=image_3,
            store_id=store_id
        )

        # --- Salva no banco ---
        db.session.add(novo_produto)
        db.session.commit()

        flash(f'O produto "{form.name.data}" foi cadastrado com sucesso!', 'success')
        return redirect(url_for('admin.product_list', type_id=type_id))

    elif request.method == 'POST':
        print("⚠️ Erros de validação:", form.errors)


    return render_template(
        'admin/product_ins.html',
        form=form,
        marcas=marcas,
        categorias=categorias,
        cores=cores,
        tamanhos=tamanhos,
        embalagens=embalagens,
        titulo='Cadastrar Produto',
        type_id=type_id,
        tipo_nome=tipo_nome
    )

@admin_bp.route('/produto/excluir/<int:produto_id>', methods=['POST'])
@login_required
def produto_excluir(produto_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Verifica se o produto pertence à loja do usuário
    store_id = session['store_id']
    produto = Product.query.filter_by(id=produto_id, store_id=store_id).first()

    if not produto:
        flash('Produto não encontrado ou você não tem permissão para excluí-lo.', 'danger')
        # Redireciona para a lista geral se o produto não for encontrado
        return redirect(url_for('admin.product_list'))

    # Como o método é POST (confirmado pela modal), exclui o produto
    try:
        nome_produto = produto.name # Salva o nome para a mensagem
        db.session.delete(produto)
        db.session.commit()
        
        flash(f'O produto "{nome_produto}" foi excluído com sucesso!', 'success')

        # Redireciona para a lista de produtos, mantendo o filtro original (type_id)
        # Se produto.type_id for 1, redireciona para /admin/1, se for 2, para /admin/2.
        return redirect(url_for('admin.product_list', type_id=produto.type_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir o produto: {e}', 'danger')
        return redirect(url_for('admin.product_list', type_id=produto.type_id))

# ---------------- BRAND ----------------
@admin_bp.route('/brand/list')
@login_required
def brand_list():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    brands = Brand.query.filter_by(store_id=store_id).order_by(Brand.name.asc()).all()

    return render_template('admin/brand_list.html', brands=brands, titulo='Marcas')


@admin_bp.route('/brand/ins', methods=['GET', 'POST'])
@login_required
def brand_insert():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    if request.method == 'POST':
        descricao = request.form.get('descricao')
        if not descricao.strip():
            flash('Informe a descrição da marca.', 'warning')
        else:
            nova_marca = Brand(name=descricao, store_id=store_id)
            db.session.add(nova_marca)
            db.session.commit()
            flash(f'A marca "{descricao}" foi cadastrada com sucesso!', 'success')
            return redirect(url_for('admin.brand_list'))

    return render_template('admin/brand_ins.html', titulo='Nova Marca')


@admin_bp.route('/brand/upd/<int:brand_id>', methods=['GET', 'POST'])
@login_required
def brand_update(brand_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    marca = Brand.query.get_or_404(brand_id)

    if request.method == 'POST':
        nova_descricao = request.form.get('descricao')
        if not nova_descricao.strip():
            flash('A descrição não pode estar vazia.', 'warning')
        else:
            marca.name = nova_descricao
            db.session.commit()
            flash('Marca atualizada com sucesso!', 'success')
            return redirect(url_for('admin.brand_list'))

    return render_template('admin/brand_upd.html', marca=marca, titulo='Editar Marca')


@admin_bp.route('/brand/del/<int:brand_id>', methods=['POST'])
@login_required
def brand_delete(brand_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    marca = Brand.query.get_or_404(brand_id)

    try:
        db.session.delete(marca)
        db.session.commit()
        flash(f'A marca "{marca.name}" foi excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a marca: {e}', 'danger')

    return redirect(url_for('admin.brand_list'))

# ---------------- CATEGORY ----------------
@admin_bp.route('/category/list')
@login_required
def category_list():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    # Busca todas as categorias da loja e ordena pelo nome
    categories = Category.query.filter_by(store_id=store_id).order_by(Category.name.asc()).all()

    return render_template('admin/category_list.html', categories=categories, titulo='Categorias')


@admin_bp.route('/category/ins', methods=['GET', 'POST'])
@login_required
def category_insert():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    if request.method == 'POST':
        descricao = request.form.get('descricao')
        if not descricao or not descricao.strip():
            flash('Informe a descrição da categoria.', 'warning')
        else:
            nova_categoria = Category(name=descricao, store_id=store_id)
            db.session.add(nova_categoria)
            db.session.commit()
            flash(f'A categoria "{descricao}" foi cadastrada com sucesso!', 'success')
            return redirect(url_for('admin.category_list'))

    return render_template('admin/category_ins.html', titulo='Nova Categoria')


@admin_bp.route('/category/upd/<int:category_id>', methods=['GET', 'POST'])
@login_required
def category_update(category_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Busca a categoria ou retorna 404
    categoria = Category.query.get_or_404(category_id)

    if request.method == 'POST':
        nova_descricao = request.form.get('descricao')
        if not nova_descricao or not nova_descricao.strip():
            flash('A descrição não pode estar vazia.', 'warning')
        else:
            categoria.name = nova_descricao
            db.session.commit()
            flash('Categoria atualizada com sucesso!', 'success')
            return redirect(url_for('admin.category_list'))

    return render_template('admin/category_upd.html', categoria=categoria, titulo='Editar Categoria')


@admin_bp.route('/category/del/<int:category_id>', methods=['POST'])
@login_required
def category_delete(category_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Busca a categoria ou retorna 404
    categoria = Category.query.get_or_404(category_id)

    try:
        nome_categoria = categoria.name # Salva o nome para a mensagem
        db.session.delete(categoria)
        db.session.commit()
        flash(f'A categoria "{nome_categoria}" foi excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        # Se houver erro (ex: chave estrangeira), informa
        flash(f'Erro ao excluir a categoria: {e}', 'danger')

    return redirect(url_for('admin.category_list'))

# No routes.py
# ... (Blocos BRAND e CATEGORY acima)

# ---------------- COLOR ----------------
@admin_bp.route('/color/list')
@login_required
def color_list():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    # Busca todas as cores da loja e ordena pelo nome
    colors = Color.query.filter_by(store_id=store_id).order_by(Color.name.asc()).all()

    return render_template('admin/color_list.html', colors=colors, titulo='Cores')


# ---------------- COLOR ----------------
# ... (color_list não precisa de alteração)


@admin_bp.route('/color/ins', methods=['GET', 'POST'])
@login_required
def color_ins(): # Rota padronizada
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    if request.method == 'POST':
        descricao = request.form.get('descricao')
        # REMOVIDA: A linha que buscava 'codigo_html'
        
        if not descricao or not descricao.strip():
            flash('Informe a descrição da cor.', 'warning')
        else:
            # CORREÇÃO: Removido o argumento 'html_code' na criação do objeto
            nova_cor = Color(name=descricao, store_id=store_id)
            db.session.add(nova_cor)
            db.session.commit()
            flash(f'A cor "{descricao}" foi cadastrada com sucesso!', 'success')
            return redirect(url_for('admin.color_list'))

    return render_template('admin/color_ins.html', titulo='Nova Cor')


@admin_bp.route('/color/upd/<int:color_id>', methods=['GET', 'POST'])
@login_required
def color_upd(color_id): # Rota padronizada
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Busca a cor ou retorna 404
    cor = Color.query.get_or_404(color_id)

    if request.method == 'POST':
        nova_descricao = request.form.get('descricao')
        # REMOVIDA: A linha que buscava 'codigo_html'
        
        if not nova_descricao or not nova_descricao.strip():
            flash('A descrição não pode estar vazia.', 'warning')
        else:
            cor.name = nova_descricao
            # REMOVIDA: A linha que tentava atualizar cor.html_code
            db.session.commit()
            flash('Cor atualizada com sucesso!', 'success')
            return redirect(url_for('admin.color_list'))

    return render_template('admin/color_upd.html', cor=cor, titulo='Editar Cor')



@admin_bp.route('/color/del/<int:color_id>', methods=['POST'])
@login_required
def color_del(color_id): # Rota padronizada
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Busca a cor ou retorna 404
    cor = Color.query.get_or_404(color_id)

    try:
        nome_cor = cor.name
        db.session.delete(cor)
        db.session.commit()
        flash(f'A cor "{nome_cor}" foi excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        # Se houver erro (ex: chave estrangeira), informa
        flash(f'Erro ao excluir a cor: {e}', 'danger')

    return redirect(url_for('admin.color_list'))

    # No routes.py, após o bloco de CORES

# ---------------- SIZE (TAMANHOS) ----------------
@admin_bp.route('/size/list')
@login_required
def size_list():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    # Busca todos os tamanhos da loja e ordena pelo nome
    sizes = Size.query.filter_by(store_id=store_id).order_by(Size.name.asc()).all()

    return render_template('admin/size_list.html', sizes=sizes, titulo='Tamanhos')


@admin_bp.route('/size/ins', methods=['GET', 'POST'])
@login_required
def size_ins():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    if request.method == 'POST':
        descricao = request.form.get('descricao')
        
        if not descricao or not descricao.strip():
            flash('Informe a descrição do tamanho.', 'warning')
        else:
            # Cria um novo Tamanho (Size)
            novo_tamanho = Size(name=descricao, store_id=store_id)
            db.session.add(novo_tamanho)
            db.session.commit()
            flash(f'O tamanho "{descricao}" foi cadastrado com sucesso!', 'success')
            return redirect(url_for('admin.size_list'))

    return render_template('admin/size_ins.html', titulo='Novo Tamanho')


@admin_bp.route('/size/upd/<int:size_id>', methods=['GET', 'POST'])
@login_required
def size_upd(size_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Busca o tamanho ou retorna 404
    tamanho = Size.query.get_or_404(size_id)

    if request.method == 'POST':
        nova_descricao = request.form.get('descricao')
        
        if not nova_descricao or not nova_descricao.strip():
            flash('A descrição não pode estar vazia.', 'warning')
        else:
            tamanho.name = nova_descricao
            db.session.commit()
            flash('Tamanho atualizado com sucesso!', 'success')
            return redirect(url_for('admin.size_list'))

    return render_template('admin/size_upd.html', tamanho=tamanho, titulo='Editar Tamanho')


@admin_bp.route('/size/del/<int:size_id>', methods=['POST'])
@login_required
def size_del(size_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Busca o tamanho ou retorna 404
    tamanho = Size.query.get_or_404(size_id)

    try:
        nome_tamanho = tamanho.name
        db.session.delete(tamanho)
        db.session.commit()
        flash(f'O tamanho "{nome_tamanho}" foi excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        # Se houver erro (ex: chave estrangeira), informa
        flash(f'Erro ao excluir o tamanho: {e}', 'danger')


# No routes.py, após o bloco de TAMANHOS

# ---------------- PACKAGING (EMBALAGENS) ----------------
@admin_bp.route('/packaging/list')
@login_required
def packaging_list():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    # Busca todas as embalagens da loja e ordena pelo nome
    packagings = Packaging.query.filter_by(store_id=store_id).order_by(Packaging.id.desc()).all()

    return render_template('admin/packaging_list.html', packagings=packagings, titulo='Embalagens')


@admin_bp.route('/packaging/ins', methods=['GET', 'POST'])
@login_required
def packaging_ins():
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    parametrosloja()
    store_id = session['store_id']

    if request.method == 'POST':
        format = request.form.get('format')
        weight = request.form.get('weight')
        length = request.form.get('length')
        height = request.form.get('height')
        width = request.form.get('width')

        if format == "1":
            format_name = "Caixa/Pacote"
        elif format == "2":
            format_name = "Rolo/Prisma"
        else:
            format_name = "Envelope"


        # Cria uma nova Embalagem (Packaging)
        nova_embalagem = Packaging(format=format, weight=weight, length=length, height=height,
                               width=width, store_id=store_id)

        try:
            db.session.add(nova_embalagem)
            flash(f'A embalagem {format_name} foi cadastrada com sucesso!', 'success')
            db.session.commit()
        except Exception as erro:
            db.session.rollback()
            flash(f'A embalagem {format_name}|{erro} não foi cadastrado, verifique se a mesma já foi cadastrada!', 'success')
        return redirect(url_for('admin.packaging_list'))



    return render_template('admin/packaging_ins.html', titulo='Nova Embalagem')


@admin_bp.route('/packaging/upd/<int:packaging_id>', methods=['GET', 'POST'])
@login_required
def packaging_upd(packaging_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Busca a embalagem ou retorna 404
    embalagem = Packaging.query.get_or_404(packaging_id)
    
    if request.method == 'POST':
        nova_descricao = request.form.get('descricao')
        novo_format = request.form.get('format')
        novo_weight = request.form.get('weight')
        novo_length = request.form.get('length')
        novo_height = request.form.get('height')
        novo_width = request.form.get('width')
        
        try:

            # Conversão e validação dos campos numéricos
            nw_float = safe_float_conversion(novo_weight, 'Peso')
            nl_float = safe_float_conversion(novo_length, 'Comprimento')
            nh_float = safe_float_conversion(novo_height, 'Altura')
            nwi_float = safe_float_conversion(novo_width, 'Largura')
            nf_int = int(novo_format)

            # Validação extra de limites para Formato
            if nf_int not in FORMAT_DESCRIPTIONS:
                raise ValueError('O formato selecionado é inválido.')
            
            # Atualiza todos os campos
            embalagem.name = nova_descricao
            embalagem.format = nf_int
            embalagem.weight = nw_float
            embalagem.length = nl_float
            embalagem.height = nh_float
            embalagem.width = nwi_float
            
            db.session.commit()
            flash('Embalagem atualizada com sucesso!', 'success')
            return redirect(url_for('admin.packaging_list'))
            
        except ValueError as e:
            flash(str(e), 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar embalagem: {e}', 'danger')
        
    # GET ou falha no POST: Calcula discformat para o template
    discformat = get_format_description(embalagem.format)
    
    return render_template('admin/packaging_upd.html', embalagem=embalagem, discformat=discformat, titulo='Editar Embalagem')

@admin_bp.route('/packaging/del/<int:packaging_id>', methods=['POST'])
@login_required
def packaging_del(packaging_id):
    if 'email' not in session:
        flash('Favor fazer login primeiro!', 'danger')
        return redirect(url_for('auth.login', origin='admin'))

    # Busca a embalagem ou retorna 404
    embalagem = Packaging.query.get_or_404(packaging_id)

    try:
        # 1. Busca a descrição do formato usando a função auxiliar
        format_description = get_format_description(embalagem.format)

        # 2. Cria uma descrição completa para a mensagem de flash
        # (Combina o nome e o formato para ser mais informativo)
        descricao_completa = f"({format_description})"

        db.session.delete(embalagem)
        db.session.commit()
        # 3. Usa a descrição completa na mensagem de sucesso
        flash(f'A embalagem "{descricao_completa}" foi excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        # Se houver erro (ex: chave estrangeira), informa
        flash(f'Erro ao excluir a embalagem: {e}', 'danger')

    return redirect(url_for('admin.packaging_list'))
