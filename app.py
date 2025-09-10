import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, flash
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env (apenas local)
load_dotenv()

# Variáveis de e-mail
email = os.getenv('EMAIL')
senha = os.getenv('SENHA')

app = Flask(__name__)

# ------------------
# CONFIGURAÇÕES
# ------------------
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'roeland')

# Banco de dados: PlanetScale (Render) ou MySQL local
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://root:roeland@localhost:3306/ouvitech'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Importar extensões
from admin import admin_bp, db, bcrypt, migrate
app.register_blueprint(admin_bp)

db.init_app(app)
bcrypt.init_app(app)
migrate.init_app(app, db)

# ------------------
# ROTAS
# ------------------
@app.route('/hello-world')
def redirect_hello():
    return redirect("/", code=301)

@app.route('/googlec4c2cad7f9951bca.html')
def google_verify():
    return "google-site-verification: googlec4c2cad7f9951bca.html", 200, {'Content-Type': 'text/plain'}

@app.route('/robots.txt')
def robots_txt():
    with open('static/robots.txt', 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    with open('static/sitemap.xml', 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'application/xml'}

@app.route('/')
def home():
    return render_template('index.html', description="Ouvirtiba Aparelhos Auditivos – Alta tecnologia Rexton e atendimento em Araquari.")

@app.route('/sobre')
def sobre():
    return render_template('sobre.html', description="Conheça a Ouvirtiba e nossa parceria com a Clínica Makasi para oferecer aparelhos auditivos Rexton.")

@app.route('/produtos')
def produtos():
    return render_template('produtos.html', description="Confira nossos aparelhos auditivos Rexton, fala mais nítida, redução automática de ruídos e conectividade com celular")

@app.route('/contato', methods=['GET', 'POST'])
def contato():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email_form = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        mensagem = request.form.get('mensagem', '').strip()

        try:
            corpo_email = f"Nome: {nome}\nE-mail: {email_form}\nTelefone: {telefone}\n\nMensagem:\n{mensagem}"
            msg = MIMEText(corpo_email)
            msg['Subject'] = 'Formulário de Contato - Site'
            msg['From'] = email_form
            msg['To'] = 'roeland.e.janssen@gmail.com'

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(email, senha)
                smtp.send_message(msg)

            flash('Mensagem enviada com sucesso, em breve entraremos em contato !', 'sucesso')
        except Exception as e:
            print(e)
            flash('Erro ao enviar mensagem. Tente novamente.', 'erro')

    return render_template('contato.html', description="Entre em contato com a Ouvirtiba para agendar seu atendimento e teste de aparelhos auditivos.")

@app.route('/blog')
def blog():
    return render_template('blog.html', description="Dicas no Blog Ouvirtiba para adaptação e uso de aparelhos auditivos, e como identificar a perda auditiva")

@app.route('/blog/dicas-adaptacao-aparelho')
def dicas_adaptacao():
    return render_template('dicas-adaptacao-aparelho.html', description="Dicas para adaptação de aparelhos auditivos")

@app.route('/blog/uso-aparelhos-auditivos')
def uso_aparelhos_auditivos():
    return render_template('uso-aparelhos-auditivos.html', description="Benefícios de usar aparelhos auditivos")

@app.route('/blog/como-identificar-perda-auditiva')
def como_identificar_perda_auditiva():
    return render_template('como-identificar-perda-auditiva.html', description="Como identificar a perda auditiva")

@app.route('/politica')
def politica():
    return render_template('politica.html', description="A Ouvirtiba Aparelhos Auditivos respeita a sua privacidade e está comprometida em proteger seus dados pessoais.")

# ------------------
# MAIN
# ------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
