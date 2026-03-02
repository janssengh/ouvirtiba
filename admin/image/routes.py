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
    
    # Determina quais pastas ler
    # Se folder_filter for 'blog', lê apenas blog. Se for 'admin', apenas admin.
    # Se for None, lê ambos.
    folders_to_read = []
    if folder_filter:
        if folder_filter in IMAGE_FOLDERS:
            folders_to_read = [(folder_filter, IMAGE_FOLDERS[folder_filter])]
    else:
        folders_to_read = list(IMAGE_FOLDERS.items())

    for category, folder in folders_to_read:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                # Filtra apenas extensões de imagem
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                    filepath = os.path.join(folder, filename)
                    try:
                        stats = os.stat(filepath)
                        # Criamos o dicionário garantindo que todas as chaves existam
                        all_images.append({
                            'name': filename,
                            'category': category,
                            'timestamp': stats.st_mtime, # Valor numérico para o sort
                            'date': datetime.fromtimestamp(stats.st_mtime).strftime('%d/%m/%Y %H:%M'),
                            'size': round(stats.st_size / 1024, 2)
                        })
                    except Exception as e:
                        # Pula arquivos que derem erro de leitura (ex: permissão)
                        continue

    # Agora a ordenação é segura, pois 'timestamp' foi adicionado no append acima
    if all_images:
        all_images.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    # Título para o template
    titulo_map = {'blog': 'Imagens do Blog', 'admin': 'Imagens Gerais (Admin)'}
    titulo = titulo_map.get(folder_filter, "Todas as Imagens")

    return render_template('admin/image/image_list.html', 
                           images=all_images, 
                           titulo=titulo, 
                           current_filter=folder_filter)

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