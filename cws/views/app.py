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


@bp.route('/status')
@login_required
def get_app_status():
    heavy_load = current_app.redis_manager.get_app_status_heavy_load()
    error = current_app.redis_manager.get_app_status_error()
    status = current_app.redis_manager.get_app_status()

    return {
        'heavy_load': heavy_load,
        'error': error,
        'status': status
    }


@bp.route('/errors')
@login_required
def get_last_errors():
    errors = ','.join(current_app.redis_manager.get_last_errors())

    response = Response('{"errors": [%s]}' % errors)
    response.headers['Content-Type'] = 'application/json'

    return response
