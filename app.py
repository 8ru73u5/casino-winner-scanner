from flask import Flask, _app_ctx_stack
from flask_apscheduler import APScheduler
from sqlalchemy.orm import scoped_session

from cws.config import AppConfig
from cws.core.scanner import Scanner
from cws.core.status_monitor import StatusMonitor
from cws.database import SessionLocal
from cws.redis_manager import RedisManager
from cws.views.app import bp as app_bp
from cws.views.auth import bp as auth_bp
from cws.views.bots import bp as bot_bp
from cws.views.config import bp as config_bp
from cws.views.place_bet import bp as place_bet_bp


def init_app(launch_core: bool = True):
    app = Flask(__name__)
    app.secret_key = AppConfig.get(AppConfig.Variables.SECRET_KEY)

    # Database
    app.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack.__ident_func__)

    # Redis
    app.redis_manager = RedisManager()

    if launch_core:
        # Core
        # noinspection PyTypeChecker
        scanner = Scanner(scoped_session(SessionLocal))

        # Status monitor
        status_monitor = StatusMonitor()

        # Scheduler
        scheduler = APScheduler(app=app)
        scheduler.add_job(func=scanner.cycle, trigger='interval', seconds=2, id='Scanner cycle')
        scheduler.add_listener(status_monitor.scheduler_monitor, StatusMonitor.SUBSCRIBED_EVENTS)
        scheduler.start()

    # Blueprints
    app.register_blueprint(app_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(bot_bp)
    app.register_blueprint(place_bet_bp)

    return app


if __name__ == '__main__':
    application = init_app()
    application.run(debug=True, use_reloader=False)
