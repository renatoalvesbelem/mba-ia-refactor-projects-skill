from functools import wraps

from flask import current_app, request

from middlewares.error_handler import AuthError, ServiceUnavailableError


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        if not expected:
            raise ServiceUnavailableError("Endpoint administrativo desabilitado: configure ADMIN_TOKEN")
        if request.headers.get("X-Admin-Token") != expected:
            raise AuthError("Token administrativo inválido")
        return view(*args, **kwargs)

    return wrapper
