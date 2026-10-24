import logging

from flask import jsonify

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(AppError):
    status_code = 400


class NotFoundError(AppError):
    status_code = 404


class AuthError(AppError):
    status_code = 401


class ConflictError(AppError):
    status_code = 409


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.message, "sucesso": False}), err.status_code

    @app.errorhandler(404)
    def handle_not_found(_err):
        return jsonify({"erro": "Recurso não encontrado", "sucesso": False}), 404

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("erro não tratado")
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500
