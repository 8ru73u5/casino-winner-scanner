from flask import Flask, _app_ctx_stack
from flask_apscheduler import APScheduler
from sqlalchemy.orm import scoped_session

from cws.config import AppConfig
from cws.core.scanner import Scanner
from cws.database import SessionLocal
from cws.redis_manager import RedisManager
from cws.views.app import bp as app_bp
from cws.views.config import bp as config_bp
from cws.views.auth import bp as auth_bp


def init_app(launch_core: bool = True):
    app = Flask(__name__)
    app.secret_key = AppConfig.get(AppConfig.Variables.SECRET_KEY)

    # Database
    app.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack.__ident_func__)

    # Redis
    app.redis_manager = RedisManager()

    if launch_core:
        # Core
        scanner = Scanner(scoped_session(SessionLocal))

        # Scheduler
        scheduler = APScheduler(app=app)
        scheduler.add_job(func=scanner.cycle, trigger='interval', seconds=5, id='Scanner cycle')
        scheduler.start()

    # Blueprints
    app.register_blueprint(app_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(config_bp)

    return app


if __name__ == '__main__':
    application = init_app()
    application.run(debug=True, use_reloader=False)
