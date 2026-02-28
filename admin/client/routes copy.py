from flask import Blueprint, session, render_template, redirect, url_for, flash, request 
from .models import Client, db 
from datetime import datetime # ✅ Certifique-se desta importação

# Importações dos seus formulários
from .forms import FormClientPFJ, FormClientDiv, FormClientPFJCompleto, FormClientDivCompleto, FormClientAddress

client_bp = Blueprint('client_bp', __name__, template_folder='templates')

@client_bp.route('/admin/client/list')
def client_list():
    clients = Client.query.all()
    # Se houver um link para o cadastro nesta template, ele DEVE apontar para 'client_bp.client_register_start'
    return render_template('admin/client/client_list.html', clients=clients)

# =========================================================
# FLUXO DE CADASTRO DE CLIENTE MULTI-STEP
# =========================================================

# ✅ ROTA 1.1 (GET): Carrega o formulário de cadastro de dados pessoais
# Endpoint RENOMEADO para client_bp.client_register_start (conforme sugestão do Flask)
@client_bp.route('/cliente/cadastrar', methods=['GET']) 
def client_register_start():
    # Esta rota carrega a tela inicial de cadastro
    form = FormClientPFJ()
    return render_template('client/client_create_personal_data.html', 
                           form=form, 
                           titulo="Registrar Novo Cliente", 
                           stperson="active")

# ✅ ROTA 1.2 (POST): Rota de Processamento do Passo 1 (Validação)
# Endpoint: client_bp.client_register_proximo_passo
@client_bp.route('/cliente/proximo_passo', methods=['POST']) 
def client_register_proximo_passo():
    """
    Processa o envio do formulário de dados pessoais, ativando as validações.
    Resolve o erro 404 que estava ocorrendo no POST.
    """
    form = FormClientPFJ()
    
    # ✅ 1. ATIVAÇÃO DA VALIDAÇÃO
    if form.validate_on_submit():
        # Se a validação for OK.
        try:
            # Lógica para determinar o tipo e salvar na sessão
            code_data = ''.join(filter(str.isdigit, form.code.data or ''))
            client_type = 'F' if len(code_data) == 11 else ('J' if len(code_data) == 14 else 'D')
            
            ############################################
            # 1. Finaliza a lógica do campo 'code' (CPF/CNPJ/Diversos)
            final_code = code_data # Código limpo da sessão
            
            if client_type == 'D':
                # ✅ Lógica para gerar DDMMAA inteiro numérico
                # Formato: DDMMYY (6 dígitos) + um identificador para unicidade
                
                # 1. Data DDMMAA
                date_str = datetime.now().strftime('%d%m%y') # Ex: 161025
                
                # 2. Sufixo para garantir Unicidade (ex: 4 dígitos baseados no tempo/milisegundos)
                # O campo 'code' tem 14 caracteres. 6 (DDMMAA) + 8 de sufixo.
                # Para maior segurança, usaremos a hora, minuto, segundo e milissegundo.
                suffix = datetime.now().strftime('%H%M%S%f')[:8]
                
                # 3. Código final (DDMMAA + Suffix)
                final_code = f"{date_str}{suffix}" 
                # O resultado terá 14 caracteres (6 da data + 8 do timestamp) e será único.
            
            # Nota: Se for 'F' ou 'J', 'final_code' já terá o CPF/CNPJ limpo (11 ou 14 dígitos).
            ############################################

            # Armazenar dados básicos na session
            session['client_reg_data'] = { 
                'code': final_code, 
                'name': form.name.data,
                'contact': ''.join(filter(str.isdigit, form.contact.data)),
                'email': form.email.data,
                'type': client_type,
                'store_id': session['store_id']
            }
            
            flash('Dados Pessoais validados com sucesso. Prossiga com o endereço.', 'info')
            return redirect(url_for('client_bp.client_register_address'))

        except Exception as e:
            flash(f'Erro interno ao processar dados. {e}', 'danger')
            
    # ✅ 2. SE A VALIDAÇÃO FALHAR:
    else:
        flash('Por favor, corrija os erros nos campos antes de continuar.', 'warning')
        
    # Renderiza o template de dados pessoais novamente, agora com os erros
    return render_template('client/client_create_personal_data.html', 
                           form=form, 
                           titulo="Registrar Novo Cliente", 
                           stperson="active")


# ROTA 2: CADASTRO DE CLIENTE - ENDEREÇO
@client_bp.route('/cliente/endereco', methods=['GET'])
def client_register_address():
    # 1. Verificar se o Passo 1 foi concluído
    if 'client_reg_data' not in session:
        flash('Por favor, preencha os dados básicos antes de prosseguir.', 'warning')
        # ✅ CORRIGIDO: Redireciona para o novo endpoint de início de cadastro
        return redirect(url_for('client_bp.client_register_start')) 

    form = FormClientAddress()
    return render_template('client/client_create_address.html', form=form, titulo="Registrar Novo Cliente - Endereço", stperson="active")


# ROTA 3: SALVAR NO BANCO DE DADOS (POST do Formulário de Endereço)
@client_bp.route('/cliente/salvar', methods=['POST'])
def client_save():
    # 1. Verificar dados da session e FormClientAddress

    if 'client_reg_data' not in session:
        flash('Sessão expirada ou dados básicos incompletos. Reinicie o cadastro.', 'danger')
        # ✅ CORRIGIDO: Redireciona para o novo endpoint de início de cadastro
        return redirect(url_for('client_bp.client_register_start'))
        
    form_address = FormClientAddress() 
    
    if form_address.validate_on_submit():

        # 4. Limpa e formata dados
        zipcode_data = ''.join(filter(str.isdigit, form_address.zipcode.data))
        
        DadosPFJD = session['client_reg_data']
        # 5. Cria a nova instância do Client
        new_client = Client(
            # Dados da Sessão (Passo 1)
            
            code=(DadosPFJD['code']),
            store_id=(DadosPFJD['store_id']),
            name=(DadosPFJD['name']),
            email=(DadosPFJD['email']),
            contact=(DadosPFJD['contact']),
            type=(DadosPFJD['type']),
            
            # Campos opcionais no modelo com defaults
            username=None, 
            profile='profile.jpg', 
            country='Brasil',

            # Dados do Formulário de Endereço (Passo 2)
            zipcode=zipcode_data,
            address=form_address.address.data,
            number=form_address.number.data,
            complement=form_address.complement.data or None, # Salva None se o campo for vazio
            neighborhood=form_address.neighborhood.data,
            city=form_address.city.data,
            region=form_address.region.data,
        )
        # 6. Adiciona e salva no banco de dados
        db.session.add(new_client)
        db.session.commit()

        flash(f'Cliente "{new_client.name}" cadastrado com sucesso!', 'success')
        return redirect(url_for('client_bp.client_list'))
    
    # Se falhar a validação do endereço
    return render_template('client/client_create_address.html', form=form_address, titulo="Endereço", stperson="active")

# =========================================================
# ROTA DE EDIÇÃO DE CLIENTE (client_update)
# ... (restante do código não alterado) ...
# =========================================================

@client_bp.route('/admin/client/update/<int:id>', methods=['GET', 'POST'])
def client_update(id):
    updatecliente = Client.query.get_or_404(id)
    
    # 1. Seleciona a classe de formulário COMPLETA correta
    if updatecliente.type == 'D':
        FormClass = FormClientDivCompleto  # Usa o formulário com endereço para Diversos
    else:
        FormClass = FormClientPFJCompleto # Usa o formulário com endereço para PF/PJ

    # 2. Instancia o formulário
    form = FormClass()
    
    if request.method == 'POST':
        # Se for POST, tenta validar os dados enviados (o formulário COMPLETO tem todos os campos)
        if form.validate_on_submit():
            try:
                # Lógica de processamento do formulário (POST)
                updatecliente.code = form.code.data
                updatecliente.name = form.name.data
                updatecliente.contact = form.contact.data
                updatecliente.email = form.email.data
                
                # ✅ Endereço agora é acessível no formulário completo
                updatecliente.zipcode = form.zipcode.data
                updatecliente.address = form.address.data
                updatecliente.number = form.number.data
                updatecliente.complement = form.complement.data
                updatecliente.neighborhood = form.neighborhood.data
                updatecliente.city = form.city.data
                updatecliente.region = form.region.data
                updatecliente.type = form.type.data # Atualiza o tipo (se necessário)

                db.session.commit()
                flash(f'Cliente {updatecliente.name} alterado com sucesso!', 'success')
                return redirect(url_for('client_bp.client_list'))
            except Exception as erro:
                db.session.rollback()
                flash(f'Cliente não foi alterado. Erro: {erro}', 'danger')
                return redirect(url_for('client_bp.client_list'))
        
        # Se a validação falhar no POST
        if not form.name.data or form.name.data.strip() == '':
            flash('Nome deve ser obrigatório !', 'danger')

        #flash('Verifique os campos do formulário!', 'danger')
        
        
    elif request.method == 'GET':
        # Se for GET, popula o formulário com os dados do banco para exibição
        form.code.data = updatecliente.code
        form.name.data = updatecliente.name
        form.contact.data = updatecliente.contact
        form.email.data = updatecliente.email
        
        # ✅ Endereço agora é acessível no formulário completo
        form.zipcode.data = updatecliente.zipcode
        form.address.data = updatecliente.address
        form.number.data = updatecliente.number
        form.complement.data = updatecliente.complement
        form.neighborhood.data = updatecliente.neighborhood
        form.city.data = updatecliente.city
        form.region.data = updatecliente.region
        form.type.data = updatecliente.type # Popula o campo 'type' (se existir)

    # Renderiza o template de edição
    return render_template('admin/client/client_upd.html', 
                           form=form, 
                           updatecliente=updatecliente,
                           titulo="Editar Cliente")


# =========================================================
# ROTA DE EXCLUSÃO DE CLIENTE (client_del)
# ... (restante do código não alterado) ...
# =========================================================
@client_bp.route('/admin/client/del/<int:client_id>', methods=['POST'])
# Opcional: Se a segurança for necessária, adicione o decorator @login_required aqui
def client_del(client_id):
    # 1. Busca o cliente ou retorna 404
    cliente = Client.query.get_or_404(client_id)
    
    try:
        nome_cliente = cliente.name
        
        # 2. Exclui o cliente do banco de dados
        db.session.delete(cliente)
        db.session.commit()
        
        # 3. Feedback e Redirecionamento
        flash(f'O cliente "{nome_cliente}" foi excluído com sucesso!', 'success')
    
    except Exception as e:
        db.session.rollback()
        # Adicione uma mensagem de erro que ajude o usuário (ex: Foreign Key)
        flash(f'Erro ao excluir o cliente "{cliente.name}". Ele pode estar vinculado a pedidos ou outros dados. Erro: {e}', 'danger')

    # Redireciona de volta para a lista de clientes
    return redirect(url_for('client_bp.client_list'))