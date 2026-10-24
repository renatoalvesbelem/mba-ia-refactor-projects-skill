import logging
from datetime import datetime

from flask import Flask
from flask_cors import CORS
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config.settings import Config
from database import db
from middlewares.error_handler import register_error_handlers
from routes.category_routes import category_bp
from routes.report_routes import report_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    logging.basicConfig(level=logging.DEBUG if app.config["DEBUG"] else logging.INFO)

    CORS(app, origins=app.config["CORS_ORIGINS"])
    db.init_app(app)

    app.register_blueprint(task_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(report_bp)

    register_error_handlers(app)

    @app.route("/health")
    def health():
        return {"status": "ok", "timestamp": str(datetime.now())}

    @app.route("/")
    def index():
        return {"message": "Task Manager API", "version": "1.0"}

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
