from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from extension import db
from admin.models import Product, Category  # Certifique-se de importar Category
from .models import ProductAssembly
from .forms import FormProductAssembly

from datetime import datetime, timedelta # Importar timedelta ou timezone

assembly_bp = Blueprint('assembly_bp', __name__, template_folder='templates')

@assembly_bp.route('/admin/assembly/list')
def assembly_list():
    store_id = session.get('store_id')
    assemblies = ProductAssembly.query.filter_by(store_id=store_id).order_by(ProductAssembly.assembly_date.desc()).all()
    return render_template('admin/assembly/product_assembly_list.html', assemblies=assemblies)

@assembly_bp.route('/admin/assembly/create', methods=['GET', 'POST'])
def assembly_create():
    form = FormProductAssembly()
    store_id = session.get('store_id')

    # Filtros para os componentes (Base, Receptor, Oliva)
    base_units = Product.query.filter(Product.type_id == 1, Product.stock > 0, Product.store_id == store_id).all()
    form.base_unit_id.choices = [(p.id, f"{p.name} (Estoque: {p.stock})") for p in base_units]

    receptors = Product.query.join(Category).filter(Product.type_id == 2, Product.stock > 0, Category.name.ilike('receptores')).all()
    form.receptor_id.choices = [(p.id, f"{p.name} (Estoque: {p.stock})") for p in receptors]

    olivas = Product.query.join(Category).filter(Product.type_id == 2, Product.stock > 0, Category.name.ilike('olivas')).all()
    form.oliva_id.choices = [(p.id, f"{p.name} (Estoque: {p.stock})") for p in olivas]

    # Variáveis para o bloco de confirmação
    show_confirmation = False
    suggested_name = ""
    suggested_price = 0.0
    parent_product_id = None

    if request.method == 'POST':
        # Passo 1: O usuário clicou para "Gerar" (Verificar componentes)
        if 'btn_gerar' in request.form:
            base = Product.query.get(form.base_unit_id.data)
            receptor = Product.query.get(form.receptor_id.data)
            oliva = Product.query.get(form.oliva_id.data)

            # Verifica se essa combinação já existe
            existing_assembly = ProductAssembly.query.filter_by(
                base_unit_id=base.id,
                receptor_id=receptor.id,
                oliva_id=oliva.id,
                store_id=store_id
            ).first()

            if existing_assembly:
                parent_product = Product.query.get(existing_assembly.parent_product_id)
                suggested_name = parent_product.name
                parent_product_id = parent_product.id
                suggested_price = parent_product.price

            else:
                suggested_name = f"{base.name} {receptor.name} {oliva.name}"
                # Sugere o preço da base ou a soma (ajuste conforme sua regra)
                suggested_price = base.price                
            
            show_confirmation = True

        # Passo 2: O usuário confirmou o nome e a quantidade
        elif 'btn_finalizar' in request.form:
            try:
                qty = int(request.form.get('final_qty', 1))
                final_name = request.form.get('final_name')
                final_price = float(request.form.get('final_price', 0).replace(',', '.'))                
                p_id = request.form.get('parent_product_id') # Pode ser None se for novo
                base = Product.query.get(form.base_unit_id.data)
                receptor = Product.query.get(form.receptor_id.data)
                oliva = Product.query.get(form.oliva_id.data)

                # CORREÇÃO DO HORÁRIO: Ajustando para Brasília (UTC-3)
                # Se o seu servidor está em UTC, subtraímos 3 horas
                data_local = datetime.now() - timedelta(hours=3)

                # Se não existir parent_product_id, cria um novo produto na tabela Product
                if not p_id or p_id == 'None':
                    new_product = Product(
                        name=final_name,
                        type_id=3, # Produto Acabado
                        stock=0,
                        price=final_price, # Usa o preço preenchido na tela                        price=base.price, # Copia dados da base
                        brand_id=base.brand_id,
                        category_id=base.category_id,
                        color_id=base.color_id,
                        size_id=base.size_id,
                        store_id=store_id,
                        image_1=base.image_1,
                        image_2=base.image_2,
                        image_3=base.image_3,
                        discription=f"Montagem: {base.name} + {receptor.name} + {oliva.name}",
                        colors=base.colors,
                        packaging_id=base.packaging_id,
                        pub_date=data_local
                    )
                    db.session.add(new_product)
                    db.session.flush() # Para pegar o ID do novo produto
                    p_id = new_product.id
                
                # Executa a montagem
                new_assembly = ProductAssembly(
                    store_id=store_id,
                    parent_product_id=p_id,
                    base_unit_id=base.id,
                    receptor_id=receptor.id,
                    oliva_id=oliva.id,
                    quantity=qty,
                    status='CONCLUIDO',
                    assembly_date=data_local
                )
                db.session.add(new_assembly)

                # Atualiza Estoques
                base.stock -= qty
                receptor.stock -= qty
                oliva.stock -= qty
                
                final_prod = Product.query.get(p_id)
                final_prod.stock = (final_prod.stock or 0) + qty
                final_prod.name = final_name # Atualiza o nome caso tenha sido alterado
                final_prod.price = final_price # Atualiza o preço de venda

                db.session.commit()
                flash('Montagem automatizada realizada com sucesso!', 'success')
                return redirect(url_for('assembly_bp.assembly_list'))

            except Exception as e:
                db.session.rollback()
                flash(f'Erro: {str(e)}', 'danger')

    return render_template('admin/assembly/product_assembly_create.html', 
                           form=form, 
                           show_confirmation=show_confirmation, 
                           suggested_name=suggested_name,
                           parent_product_id=parent_product_id)