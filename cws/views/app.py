from flask import Blueprint, render_template

bp = Blueprint('app', __name__, url_prefix='/')


@bp.route('/')
def main():
    return render_template('main.html')
