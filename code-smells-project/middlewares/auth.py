from functools import wraps

from flask import current_app, request

from middlewares.error_handler import AuthError, AppError


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        if not expected:
            raise AppError(
                "Endpoint administrativo desabilitado: configure ADMIN_TOKEN", 503
            )
        if request.headers.get("X-Admin-Token") != expected:
            raise AuthError("Token administrativo inválido")
        return view(*args, **kwargs)

    return wrapper


def recusar_em_producao():
    if current_app.config.get("APP_ENV") == "production":
        raise AppError("Operação desabilitada em produção", 403)
