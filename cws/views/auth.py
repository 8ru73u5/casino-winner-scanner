import functools

from flask import Blueprint, render_template, request, session, url_for, redirect, g

from cws.config import AppConfig

bp = Blueprint('auth', __name__, url_prefix='/auth')


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not g.admin:
            return redirect(url_for('app.main'))

        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    g.admin = session.get('admin') is not None


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        valid_username = AppConfig.get(AppConfig.Variables.CASINO_ADMIN_USER)
        valid_password = AppConfig.get(AppConfig.Variables.CASINO_ADMIN_PASS)

        if username == valid_username and password == valid_password:
            session.clear()
            session['admin'] = True
            return redirect(url_for('app.main'))

    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('app.main'))
