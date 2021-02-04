from flask import Blueprint, render_template, current_app, Response

from cws.views.auth import login_required

bp = Blueprint('app', __name__, url_prefix='/')


@bp.route('/')
def main():
    return render_template('main.html')


@bp.route('/notifications')
@login_required
def get_notifications():
    notifications = ','.join(current_app.redis_manager.get_notifications_json())

    response = Response('{"notifications": [%s]}' % notifications)
    response.headers['Content-Type'] = 'application/json'

    return response
