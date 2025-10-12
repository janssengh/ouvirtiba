from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash('Favor fazer login primeiro!', 'danger')
            return redirect(url_for('auth.login', origin='admin'))
        return f(*args, **kwargs)
    return decorated_function
