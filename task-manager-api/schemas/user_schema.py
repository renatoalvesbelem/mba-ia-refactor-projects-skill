import re

from marshmallow import Schema, ValidationError, fields, post_load

from models.user import UserRole

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")


class UserSchema(Schema):
    name = fields.Str(allow_none=True)
    email = fields.Str(allow_none=True)
    password = fields.Str(allow_none=True)
    role = fields.Str(allow_none=True)
    active = fields.Raw(allow_none=True)

    def __init__(self, *args, password_too_short_msg="Senha deve ter no mínimo 4 caracteres", **kwargs):
        super().__init__(*args, **kwargs)
        self.password_too_short_msg = password_too_short_msg

    @post_load
    def finalize(self, data, **kwargs):
        if not self.partial:
            if not data.get("name"):
                raise ValidationError("Nome é obrigatório")
            if not data.get("email"):
                raise ValidationError("Email é obrigatório")
            if not data.get("password"):
                raise ValidationError("Senha é obrigatória")

        if "email" in data and data["email"] is not None:
            if not EMAIL_PATTERN.match(data["email"]):
                raise ValidationError("Email inválido")

        if "password" in data and data["password"] is not None:
            if len(data["password"]) < 4:
                raise ValidationError(self.password_too_short_msg)

        if "role" in data and data["role"] is not None:
            if data["role"] not in UserRole.ALL:
                raise ValidationError("Role inválido")
        elif not self.partial:
            data["role"] = UserRole.USER

        return data
