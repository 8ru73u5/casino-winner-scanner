from flask import Flask

from cws.config import AppConfig


def init_app():
    app = Flask(__name__)
    app.secret_key = AppConfig.get(AppConfig.Variables.SECRET_KEY)

    return app


if __name__ == '__main__':
    application = init_app()
    application.run(debug=True, use_reloader=False)
