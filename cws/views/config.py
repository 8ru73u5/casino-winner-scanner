from flask import Blueprint, render_template

bp = Blueprint('config', __name__, url_prefix='/config')


@bp.route('/')
def main():
    return render_template('config.html')
