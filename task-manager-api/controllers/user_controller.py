import logging

from controllers.schema_utils import load_or_raise
from database import db
from middlewares.error_handler import AuthError, ConflictError, ForbiddenError, NotFoundError, ValidationError
from models.user import User
from schemas.user_schema import UserSchema

logger = logging.getLogger(__name__)


class UserController:
    def list_all(self):
        return [user.to_dict(include_task_count=True) for user in User.query.all()]

    def get(self, user_id):
        user = self._require_user(user_id)
        data = user.to_dict()
        data["tasks"] = [task.to_dict() for task in user.tasks]
        return data

    def create(self, payload):
        data = load_or_raise(UserSchema(), payload)
        self._ensure_email_available(data["email"])
        user = User(name=data["name"], email=data["email"], role=data["role"])
        user.set_password(data["password"])
        db.session.add(user)
        db.session.commit()
        logger.info("user created id=%s", user.id)
        return user

    def update(self, user_id, payload):
        user = self._require_user(user_id)
        data = load_or_raise(UserSchema(partial=True, password_too_short_msg="Senha muito curta"), payload)
        if "email" in data:
            self._ensure_email_available(data["email"], exclude_user_id=user_id)
            user.email = data["email"]
        if "name" in data:
            user.name = data["name"]
        if "password" in data:
            user.set_password(data["password"])
        if "role" in data:
            user.role = data["role"]
        if "active" in data:
            user.active = data["active"]
        db.session.commit()
        logger.info("user updated id=%s", user.id)
        return user

    def delete(self, user_id):
        user = self._require_user(user_id)
        for task in list(user.tasks):
            db.session.delete(task)
        db.session.delete(user)
        db.session.commit()
        logger.info("user deleted id=%s", user_id)

    def list_tasks(self, user_id):
        user = self._require_user(user_id)
        return [task.to_summary_dict() for task in user.tasks]

    def login(self, payload):
        if not payload:
            raise ValidationError("Dados inválidos")
        email = payload.get("email")
        password = payload.get("password")
        if not email or not password:
            raise ValidationError("Email e senha são obrigatórios")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            raise AuthError("Credenciais inválidas")
        if not user.active:
            raise ForbiddenError("Usuário inativo")
        return user

    def _require_user(self, user_id):
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError("Usuário não encontrado")
        return user

    def _ensure_email_available(self, email, exclude_user_id=None):
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != exclude_user_id:
            raise ConflictError("Email já cadastrado")
