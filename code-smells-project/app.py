import logging

from flask import Flask
from flask_cors import CORS

from config import Config
from middlewares.error_handler import register_error_handlers
from models.base import init_app as init_db
from routes.pedido_routes import pedido_bp
from routes.produto_routes import produto_bp
from routes.sistema_routes import sistema_bp
from routes.usuario_routes import usuario_bp


def create_app(config_object=Config):
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(app, origins=app.config["CORS_ORIGINS"])

    init_db(app)
    register_error_handlers(app)

    app.register_blueprint(produto_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(pedido_bp)
    app.register_blueprint(sistema_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
