import re

from marshmallow import Schema, ValidationError, fields, post_load

COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class CategorySchema(Schema):
    name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    color = fields.Str(allow_none=True)

    @post_load
    def finalize(self, data, **kwargs):
        if not self.partial and not data.get("name"):
            raise ValidationError("Nome é obrigatório")

        if "color" in data and data["color"] is not None:
            if not COLOR_PATTERN.match(data["color"]):
                raise ValidationError("Cor inválida. Use o formato #RRGGBB")
        elif not self.partial:
            data["color"] = "#000000"

        if not self.partial:
            data.setdefault("description", "")

        return data
