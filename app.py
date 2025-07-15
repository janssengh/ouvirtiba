from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/produtos')
def produtos():
    return render_template('produtos.html')

@app.route('/contato')
def contato():
    return render_template('contato.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/politica')
def politica():
    return render_template('politica.html')

if __name__ == '__main__':
    app.run(debug=True)