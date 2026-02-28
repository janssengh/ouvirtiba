# admin/blog_post/routes.py

from flask import Blueprint, session, render_template, redirect, url_for, flash, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import re
import logging

from .models import BlogPost, db
from .forms import FormBlogPost

# 🔥 CONFIGURAÇÃO DE CAMINHO ABSOLUTO
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# admin/blog_post/routes.py está em: projeto/admin/blog_post/
# Subir 2 níveis para chegar na raiz do projeto
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '../..'))
STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'static')

print(f"🔍 DEBUG PATHS:")
print(f"   BASE_DIR: {BASE_DIR}")
print(f"   PROJECT_ROOT: {PROJECT_ROOT}")
print(f"   STATIC_FOLDER: {STATIC_FOLDER}")
print()

logging.basicConfig(level=logging.INFO)

blog_bp = Blueprint('blog_bp', __name__, template_folder='templates')

# =========================================================
# FUNÇÕES AUXILIARES - GERENCIAMENTO DE IMAGENS
# =========================================================

def extrair_imagens_do_conteudo(content):
    """
    Extrai todos os caminhos de imagens do conteúdo HTML.
    Retorna uma lista de caminhos relativos (ex: 'uploads/blog/20260217111811_image.png')
    """
    if not content:
        return []
    
    # Busca por src="/static/uploads/blog/..." ou src="uploads/blog/..."
    pattern = r'src=["\'](?:/static/)?(uploads/blog/[^"\']+)["\']'
    matches = re.findall(pattern, content)
    return list(set(matches))  # Remove duplicatas


def excluir_arquivo_fisico(caminho_relativo):
    """
    Exclui um arquivo físico do sistema de arquivos se ele existir.
    """
    if not caminho_relativo:
        print(f"      ⚠️  Caminho vazio, nada a excluir")
        return False

    try:
        # Monta caminho completo
        caminho_completo = os.path.join(STATIC_FOLDER, caminho_relativo.replace('static/', ''))
        
        print(f"      🔍 Caminho relativo: {caminho_relativo}")
        print(f"      🔍 STATIC_FOLDER: {STATIC_FOLDER}")
        print(f"      🔍 Caminho completo: {caminho_completo}")
        print(f"      🔍 Arquivo existe? {os.path.exists(caminho_completo)}")

        if os.path.exists(caminho_completo):
            os.remove(caminho_completo)
            print(f"      ✅ Arquivo excluído: {caminho_completo}")
            logging.info(f"✓ Arquivo excluído: {caminho_completo}")
            return True
        else:
            print(f"      ❌ Arquivo NÃO ENCONTRADO: {caminho_completo}")
            logging.warning(f"⚠ Arquivo não encontrado: {caminho_completo}")
            return False

    except Exception as e:
        print(f"      ❌ ERRO ao excluir: {e}")
        logging.error(f"✗ Erro ao excluir {caminho_relativo}: {e}")
        return False

def limpar_imagens_orfas(imagens_antigas, imagens_novas):
    """
    Compara listas de imagens e exclui as que não existem mais no novo conteúdo.
    
    imagens_antigas: lista de caminhos de imagens do conteúdo antigo
    imagens_novas: lista de caminhos de imagens do novo conteúdo
    """
    imagens_para_excluir = set(imagens_antigas) - set(imagens_novas)
    
    for imagem in imagens_para_excluir:
        excluir_arquivo_fisico(imagem)
    
    if imagens_para_excluir:
        print(f"✓ {len(imagens_para_excluir)} imagem(ns) órfã(s) excluída(s)")

def imagem_esta_em_uso(caminho_relativo, post_id=None):
    """
    Verifica se a imagem está sendo usada por outro post.
    """
    query = BlogPost.query.filter(
        BlogPost.content.contains(caminho_relativo)
    )

    if post_id:
        query = query.filter(BlogPost.id != post_id)

    return query.first() is not None

# =========================================================
# FUNÇÕES AUXILIARES - PROCESSAMENTO
# =========================================================

def generate_slug(title):
    """Gera um slug amigável a partir do título."""
    slug = title.lower()
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[ç]', 'c', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def save_image(image_file, upload_folder='static/uploads/blog'):
    """Salva a imagem do post e retorna o caminho relativo."""
    if image_file:
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        filename = secure_filename(image_file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(upload_folder, unique_filename)
        image_file.save(filepath)
        return f"uploads/blog/{unique_filename}"
    return None


def image_foi_enviada(form_image):
    """Verifica se uma imagem foi realmente enviada no formulário."""
    return (form_image.data and
            hasattr(form_image.data, 'filename') and
            form_image.data.filename != '')


def corrigir_caminhos_imagens(content):
    """
    Corrige caminhos relativos de imagens no conteúdo HTML gerado pelo TinyMCE
    ao colar conteúdo do Word, convertendo ../../static/... para /static/...
    """
    # Substitui qualquer caminho relativo ../../static/ ou ../static/ por /static/
    content = re.sub(r'(src=["\'])(?:\.\./)+static/', r'\1/static/', content)
    # Substitui file:/// (imagens locais do Word que não foram enviadas)
    content = re.sub(r'src=["\']file:///[^"\']*["\']', 'src="/static/img/imagem-indisponivel.png"', content)
    return content


def exibir_erros_formulario(form):
    """Exibe mensagens flash detalhadas para cada erro de validação."""
    for field_name, errors in form.errors.items():
        field = getattr(form, field_name, None)
        label = field.label.text if field and hasattr(field, 'label') else field_name
        for error in errors:
            flash(f'Campo "{label}": {error}', 'warning')

# =========================================================
# ROTAS CRUD
# =========================================================

@blog_bp.route('/admin/blog/list')
def blog_list():
    """Lista todos os posts do blog."""
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog_post/blog_list.html', posts=posts)


@blog_bp.route('/admin/blog/create', methods=['GET', 'POST'])
def blog_create():
    """Cria um novo post do blog."""
    form = FormBlogPost()

    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                slug = form.slug.data if form.slug.data else generate_slug(form.title.data)

                existing_post = BlogPost.query.filter_by(slug=slug).first()
                if existing_post:
                    flash(f'Já existe um post com o slug "{slug}". Escolha outro título ou slug.', 'warning')
                    return render_template('admin/blog_post/blog_create.html', form=form, titulo="Novo Post")

                image_path = None
                if image_foi_enviada(form.image):
                    image_path = save_image(form.image.data)

                new_post = BlogPost(
                    store_id=session.get('store_id'),
                    title=form.title.data,
                    summary=form.summary.data,
                    content=corrigir_caminhos_imagens(form.content.data),
                    author=form.author.data,
                    image=image_path,
                    slug=slug,
                    active=form.active.data,
                    created_at=datetime.now()
                )

                db.session.add(new_post)
                db.session.commit()

                flash(f'Post "{new_post.title}" criado com sucesso!', 'success')
                return redirect(url_for('blog_bp.blog_list'))

            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar no banco de dados: {str(e)}', 'danger')
        else:
            exibir_erros_formulario(form)

    return render_template('admin/blog_post/blog_create.html', form=form, titulo="Novo Post")


@blog_bp.route('/admin/blog/update/<int:id>', methods=['GET', 'POST'])
def blog_update(id):
    """Atualiza um post existente com gerenciamento inteligente de imagens."""
    post = BlogPost.query.get_or_404(id)
    form = FormBlogPost()

    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # ✅ 1. GERENCIAR IMAGEM DESTACADA (coluna 'image')
                imagem_antiga = post.image  # Guarda referência da imagem antiga
                
                if image_foi_enviada(form.image):
                    # Nova imagem foi enviada
                    nova_imagem = save_image(form.image.data)
                    if nova_imagem:
                        # Exclui a imagem antiga se existir
                        if imagem_antiga:
                            excluir_arquivo_fisico(imagem_antiga)
                        post.image = nova_imagem
                
                # ✅ 2. GERENCIAR IMAGENS DO CONTEÚDO (coluna 'content')
                conteudo_antigo = post.content
                conteudo_novo = corrigir_caminhos_imagens(form.content.data)
                
                # Extrai imagens do conteúdo antigo e novo
                imagens_antigas_conteudo = extrair_imagens_do_conteudo(conteudo_antigo)
                imagens_novas_conteudo = extrair_imagens_do_conteudo(conteudo_novo)
                
                # Limpa imagens que não existem mais no novo conteúdo
                limpar_imagens_orfas(imagens_antigas_conteudo, imagens_novas_conteudo)
                
                # ✅ 3. ATUALIZAR OUTROS CAMPOS
                post.title = form.title.data
                post.summary = form.summary.data
                post.content = conteudo_novo
                post.author = form.author.data
                post.active = form.active.data

                if form.slug.data and form.slug.data != post.slug:
                    existing_post = BlogPost.query.filter_by(slug=form.slug.data).first()
                    if existing_post and existing_post.id != post.id:
                        flash(f'Já existe um post com o slug "{form.slug.data}". Escolha outro.', 'warning')
                        return render_template('admin/blog_post/blog_upd.html', form=form, post=post)
                    post.slug = form.slug.data

                post.updated_at = datetime.now()

                db.session.commit()
                flash(f'Post "{post.title}" atualizado com sucesso!', 'success')
                return redirect(url_for('blog_bp.blog_list'))

            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar no banco de dados: {str(e)}', 'danger')
        else:
            exibir_erros_formulario(form)

    elif request.method == 'GET':
        form.title.data = post.title
        form.summary.data = post.summary
        form.content.data = post.content
        form.author.data = post.author
        form.slug.data = post.slug
        form.active.data = post.active

    return render_template('admin/blog_post/blog_upd.html', form=form, post=post)


@blog_bp.route('/admin/blog/upload-image', methods=['POST'])
def upload_image():
    """Rota exclusiva para upload de imagens pelo TinyMCE dentro do conteúdo."""
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Arquivo sem nome'}), 400

    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''

    if ext not in allowed_extensions:
        return jsonify({'error': 'Formato não permitido. Use JPG, PNG, GIF ou WEBP.'}), 400

    try:
        image_path = save_image(file)
        location = f"{request.host_url}static/{image_path}"
        return jsonify({'location': location})
    except Exception as e:
        return jsonify({'error': f'Erro ao salvar imagem: {str(e)}'}), 500


@blog_bp.route('/admin/blog/delete/<int:post_id>', methods=['POST'])
def blog_delete(post_id):
    """Exclui um post do blog com segurança e controle de imagens."""
    post = BlogPost.query.get_or_404(post_id)

    try:
        post_title = post.title
        print(f"\n{'='*60}")
        print(f"🗑️  INICIANDO EXCLUSÃO DO POST: {post_title} (ID: {post_id})")
        print(f"{'='*60}")

        # 1️⃣ IMAGEM DESTACADA
        if post.image:
            print(f"\n📸 Imagem destacada encontrada: {post.image}")
            # Verificar se outros posts usam essa mesma imagem
            outros_posts = BlogPost.query.filter(
                BlogPost.id != post.id,
                BlogPost.image == post.image
            ).count()
            
            if outros_posts > 0:
                print(f"⚠️  Imagem destacada está em uso por {outros_posts} outro(s) post(s). NÃO será excluída.")
            else:
                print(f"✅ Imagem destacada NÃO está em uso. Será excluída.")
                excluir_arquivo_fisico(post.image)
        else:
            print(f"ℹ️  Post não tem imagem destacada")

        # 2️⃣ IMAGENS DO CONTEÚDO
        imagens_conteudo = extrair_imagens_do_conteudo(post.content)
        print(f"\n🖼️  Imagens no conteúdo: {len(imagens_conteudo)}")
        
        for img in imagens_conteudo:
            print(f"\n   Processando: {img}")
            
            # Verificar se outros posts usam essa imagem no conteúdo
            outros_posts = BlogPost.query.filter(
                BlogPost.id != post.id,
                BlogPost.content.like(f'%{img}%')
            ).count()
            
            if outros_posts > 0:
                print(f"   ⚠️  Imagem está em uso por {outros_posts} outro(s) post(s). NÃO será excluída.")
            else:
                print(f"   ✅ Imagem NÃO está em uso. Será excluída.")
                excluir_arquivo_fisico(img)

        # 3️⃣ EXCLUIR DO BANCO
        print(f"\n🗄️  Excluindo post do banco de dados...")
        db.session.delete(post)
        db.session.commit()
        print(f"✅ Post excluído do banco com sucesso!")
        print(f"{'='*60}\n")

        flash(f'Post "{post_title}" excluído com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"❌ Erro ao excluir post {post.id}: {e}")
        print(f"❌ ERRO: {e}")
        flash(f'Erro ao excluir o post "{post.title}".', 'danger')

    return redirect(url_for('blog_bp.blog_list'))