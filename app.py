from flask import Flask, render_template, request, redirect, flash
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'roeland'  # Necessária para flash()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/produtos')
def produtos():
    return render_template('produtos.html')

@app.route('/contato', methods=['GET', 'POST'])
def contato():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        mensagem = request.form.get('mensagem', '').strip()

        try:
            corpo_email = f"Nome: {nome}\nE-mail: {email}\nTelefone: {telefone}\n\nMensagem:\n{mensagem}"
            msg = MIMEText(corpo_email)
            msg['Subject'] = 'Formulário de Contato - Site'
            msg['From'] = email
            msg['To'] = 'roeland.e.janssen@gmail.com'

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login('roeland.e.janssen@gmail.com', 'gscg rvmq lhot zgns')
                smtp.send_message(msg)

            flash('Mensagem enviada com sucesso, em breve entraremos em contato !', 'sucesso')
        except Exception as e:
            print(e)
            flash('Erro ao enviar mensagem. Tente novamente.', 'erro')

        return render_template('contato.html')

    return render_template('contato.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/politica')
def politica():
    return render_template('politica.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
