from flask import Flask, render_template, request, redirect, flash, send_from_directory
import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()

email = os.getenv('EMAIL')
senha = os.getenv('SENHA')


app = Flask(__name__)
app.secret_key = 'roeland'  # Necessária para flash()


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
