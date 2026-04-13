import os
from flask import Flask

from web.auth import init_auth
from web.routes import bp

# Raiz do projeto (um nível acima de web/)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(_BASE_DIR, "templates"),
        static_folder=os.path.join(_BASE_DIR, "static"),
    )
    app.secret_key = "dashboard-erros-chave-secreta-2024"
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    init_auth(app)
    app.register_blueprint(bp)
    return app
