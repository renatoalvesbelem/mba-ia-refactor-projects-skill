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


class ConflictError(AppError):
    status_code = 409


class AuthError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class ServiceUnavailableError(AppError):
    status_code = 503


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"error": err.message}), err.status_code

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({"error": "Recurso não encontrado"}), 404

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro inesperado")
        return jsonify({"error": "Erro interno"}), 500
