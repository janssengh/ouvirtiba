from flask import Flask, render_template, request, redirect, flash, send_from_directory

# Inclusão banco de dados POSTGRESQL
from flask_sqlalchemy import SQLAlchemy 

# Inclusão ENDPOINT para manter ativo o SUPABASE
from sqlalchemy import text

import resend  # ✅ NOVA BIBLIOTECA
import os
import logging
import re

from dotenv import load_dotenv
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ NOVAS VARIÁVEIS DE AMBIENTE
resend_api_key = os.getenv('RESEND_API_KEY')
email_from = os.getenv('EMAIL_FROM', 'contato@ouvirtiba.com.br')
email_to = os.getenv('EMAIL_TO', 'roeland.e.janssen@gmail.com')

# Configurar Resend
if resend_api_key:
    resend.api_key = resend_api_key
    logger.info("✅ Resend API configurada com sucesso")
else:
    logger.warning("⚠️ RESEND_API_KEY não encontrada no .env")


app = Flask(__name__)
app.secret_key = 'roeland'  # Necessária para flash()

########################## Inclusão com banco de dados ##########################
# 🔹 Configurar banco PostgreSQL (Supabase ou local)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'minha_chave_padrao')

# 🔹 Importar e inicializar banco e módulo admin
from extension import db, bcrypt         # ✅ adicionado
from admin import init_app as init_admin
from admin.client.routes import client_bp
from admin.order.routes import order_bp
from admin.nfe.routes import nfe_bp
from admin.blog_post.routes import blog_bp
from admin.purchases import purchases_bp
from admin.image.routes import image_bp

db.init_app(app)
bcrypt.init_app(app)  # ✅ adiciona essa linha

init_admin(app)
app.register_blueprint(client_bp)       
app.register_blueprint(order_bp)
app.register_blueprint(nfe_bp)
app.register_blueprint(blog_bp)
app.register_blueprint(purchases_bp)
app.register_blueprint(image_bp)

######################## Término Inclusão com banco de dados #####################

# ENDPOINT para manter ativo o SUPABASE free
@app.route("/keep-alive")
def keep_alive():
    try:
        db.session.execute(text("SELECT 1"))
        db.session.commit()
        return "OK", 200
    except Exception as e:
        import traceback
        erro_detalhado = traceback.format_exc()
        print("KEEP ALIVE ERROR:", erro_detalhado)
        return f"ERROR: {str(e)}", 500  # Retorna o erro no navegador

@app.route('/hello-world')
def redirect_hello():
    return redirect("/", code=301)

@app.route('/googlec4c2cad7f9951bca.html')
def google_verify():
    return "google-site-verification: googlec4c2cad7f9951bca.html", 200, {'Content-Type': 'text/plain'}

@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    with open('static/sitemap.xml', 'r', encoding='utf-8') as f:
        xml_content = f.read()
    return xml_content, 200, {'Content-Type': 'application/xml'}

@app.route('/')
def home():
    return render_template('index.html', description="Ouvirtiba Aparelhos Auditivos – Alta tecnologia Rexton e atendimento em Araquari.")

@app.route('/sobre')
def sobre():
    return render_template('sobre.html', description="Conheça a Ouvirtiba e nossa parceria com a Clínica Makasi para oferecer aparelhos auditivos Rexton.")

@app.route('/produtos')
def produtos():
    return render_template('produtos.html', description="Confira nossos aparelhos auditivos Rexton, fala mais nítida e redução automático de ruídos e conectividade com celular")

def validar_email(email):
    """Valida formato de email"""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

def validar_telefone(telefone):
    """Valida se tem exatamente 11 dígitos (DDD + 9 dígitos)"""
    apenas_numeros = re.sub(r'\D', '', telefone)
    return len(apenas_numeros) == 11

@app.route('/contato', methods=['GET', 'POST'])
def contato():
    if request.method == 'POST':
        # Capturar dados do formulário
        nome = request.form.get('nome', '').strip()
        email_form = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        mensagem = request.form.get('mensagem', '').strip()

        # Validações no backend
        if not nome or len(nome) < 3:
            flash('Por favor, informe seu nome completo.', 'erro')
            return render_template('contato.html', 
                                 nome=nome, 
                                 email=email_form, 
                                 telefone=telefone, 
                                 mensagem=mensagem,
                                 description="Entre em contato com a Ouvirtiba para agendar seu atendimento e teste de aparelhos auditivos.")

        if not email_form or not validar_email(email_form):
            flash('Por favor, informe um e-mail válido.', 'erro')
            return render_template('contato.html', 
                                 nome=nome, 
                                 email=email_form, 
                                 telefone=telefone, 
                                 mensagem=mensagem,
                                 description="Entre em contato com a Ouvirtiba para agendar seu atendimento e teste de aparelhos auditivos.")

        if not telefone or not validar_telefone(telefone):
            flash('Por favor, informe um telefone válido com DDD + 9 dígitos. Exemplo: (47) 99999-8888', 'erro')
            return render_template('contato.html', 
                                 nome=nome, 
                                 email=email_form, 
                                 telefone=telefone, 
                                 mensagem=mensagem,
                                 description="Entre em contato com a Ouvirtiba para agendar seu atendimento e teste de aparelhos auditivos.")

        if not mensagem or len(mensagem) < 10:
            flash('Por favor, escreva uma mensagem com pelo menos 10 caracteres.', 'erro')
            return render_template('contato.html', 
                                 nome=nome, 
                                 email=email_form, 
                                 telefone=telefone, 
                                 mensagem=mensagem,
                                 description="Entre em contato com a Ouvirtiba para agendar seu atendimento e teste de aparelhos auditivos.")

        # Verificar se API key do Resend está configurada
        if not resend_api_key:
            logger.error("❌ ERRO: Variável de ambiente RESEND_API_KEY não configurada!")
            flash('Erro de configuração do servidor. Entre em contato pelo WhatsApp.', 'erro')
            return render_template('contato.html', 
                                 nome=nome, 
                                 email=email_form, 
                                 telefone=telefone, 
                                 mensagem=mensagem,
                                 description="Entre em contato com a Ouvirtiba para agendar seu atendimento e teste de aparelhos auditivos.")

        try:
            # Log de tentativa de envio
            logger.info(f"📧 Tentando enviar email via Resend de: {email_form}")
            
            # ✅ ENVIAR EMAIL COM RESEND
            corpo_html = f"""
            <h2>Novo contato do site Ouvirtiba</h2>
            <p><strong>Nome:</strong> {nome}</p>
            <p><strong>E-mail:</strong> {email_form}</p>
            <p><strong>Telefone:</strong> {telefone}</p>
            <h3>Mensagem:</h3>
            <p>{mensagem.replace(chr(10), '<br>')}</p>
            """
            
            params = {
                "from": f"Ouvirtiba <{email_from}>",
                "to": [email_to],
                "reply_to": email_form,  # Email do usuário para resposta
                "subject": "Formulário de Contato - Site Ouvirtiba",
                "html": corpo_html,
            }
            
            # Enviar email
            email_response = resend.Emails.send(params)
            logger.info(f"✅ Email enviado com sucesso! ID: {email_response.get('id', 'N/A')}")

            flash('Mensagem enviada com sucesso! Em breve entraremos em contato.', 'sucesso')
            
            # Limpar campos após sucesso
            return redirect('/contato')

        except Exception as e:
            logger.error(f"❌ ERRO AO ENVIAR EMAIL: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Mensagem amigável para o usuário
            flash('Erro ao enviar mensagem. Por favor, entre em contato pelo WhatsApp.', 'erro')

        # Manter dados preenchidos em caso de erro
        return render_template('contato.html', 
                             nome=nome, 
                             email=email_form, 
                             telefone=telefone, 
                             mensagem=mensagem,
                             description="Entre em contato com a Ouvirtiba para agendar seu atendimento e teste de aparelhos auditivos.")

    return render_template('contato.html', description="Entre em contato com a Ouvirtiba para agendar seu atendimento e teste de aparelhos auditivos.")


@app.route('/blog')
def blog():
    return render_template('blog.html', description="Dicas no Blog Ouvirtiba, para adaptação e uso de aparelhos auditivos, e como identificar a perda auditiva")

@app.route('/blog/dicas-adaptacao-aparelho')
def dicas_adaptacao():
    return render_template('dicas-adaptacao-aparelho.html', description="Dicas para adaptação de aparelhos auditivos")

@app.route('/blog/uso-aparelhos-auditivos')
def uso_aparelhos_auditivos():
    return render_template('uso-aparelhos-auditivos.html', description="Benefícios para usar aparelhos auditivos")

@app.route('/blog/como-identificar-perda-auditiva')
def como_identificar_perda_auditiva():
    return render_template('como-identificar-perda-auditiva.html', description="Como identificar a perda auditiva")

@app.route('/politica')
def politica():
    return render_template('politica.html', description="A Ouvirtiba Aparelhos Auditivos respeita a sua privacidade e está comprometida em proteger seus dados pessoais.")

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)