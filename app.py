from flask import Flask, _app_ctx_stack
from sqlalchemy.orm import scoped_session

from cws.config import AppConfig
from cws.database import SessionLocal


def init_app():
    app = Flask(__name__)
    app.secret_key = AppConfig.get(AppConfig.Variables.SECRET_KEY)

    # Database
    app.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack.__ident_func__)

    return app


if __name__ == '__main__':
    application = init_app()
    application.run(debug=True, use_reloader=False)
