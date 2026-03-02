import os
from flask import Blueprint, render_template, redirect, url_for, flash, session
from datetime import datetime

image_bp = Blueprint('image_bp', __name__, template_folder='templates')

# Configuração das pastas de imagens
IMAGE_FOLDERS = {
    'blog': 'static/uploads/blog',
    'admin': 'static/img/admin'
}

@image_bp.route('/admin/image/list')
@image_bp.route('/admin/image/list/<folder_filter>')
def image_list(folder_filter=None):

    all_images = []
    
    # Define quais pastas ler com base no filtro
    folders_to_read = IMAGE_FOLDERS.items()
    if folder_filter and folder_filter in IMAGE_FOLDERS:
        folders_to_read = [(folder_filter, IMAGE_FOLDERS[folder_filter])]

    for category, folder in folders_to_read:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    filepath = os.path.join(folder, filename)
                    stats = os.stat(filepath)
                    all_images.append({
                        'name': filename,
                        'category': category,
                        'date': datetime.fromtimestamp(stats.st_mtime).strftime('%d/%m/%Y %H:%M'),
                        'size': round(stats.st_size / 1024, 2)
                    })

    # ORDENAÇÃO: Lambda que ordena pelo timestamp de forma decrescente (mais recentes primeiro)
    all_images.sort(key=lambda x: x['timestamp'], reverse=True)

    # Título dinâmico para a página
    titulo = "Todas as Imagens"
    if folder_filter == 'blog': titulo = "Imagens do Blog"
    elif folder_filter == 'admin': titulo = "Imagens Gerais (Admin)"

    return render_template('admin/image/image_list.html', images=all_images, titulo=titulo)

@image_bp.route('/admin/image/view/<category>/<filename>')
def image_view(category, filename):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
        
    return render_template('admin/image/image_view.html', category=category, filename=filename)

@image_bp.route('/admin/image/delete/<category>/<filename>', methods=['POST'])
def image_delete(category, filename):
    if category not in IMAGE_FOLDERS:
        flash("❌ Categoria inválida!", "danger")
        return redirect(url_for('image_bp.image_list'))

    filepath = os.path.join(IMAGE_FOLDERS[category], filename)
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            flash(f"✅ Imagem '{filename}' removida com sucesso!", "success")
        else:
            flash("❌ Arquivo não encontrado.", "warning")
    except Exception as e:
        flash(f"❌ Erro ao excluir: {str(e)}", "danger")

    return redirect(url_for('image_bp.image_list'))