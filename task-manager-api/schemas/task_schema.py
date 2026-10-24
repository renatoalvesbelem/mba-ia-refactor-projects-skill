from datetime import datetime

from marshmallow import Schema, ValidationError, fields, post_load

from models.task import Task, TaskStatus


class TaskSchema(Schema):
    title = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True)
    priority = fields.Raw(allow_none=True)
    user_id = fields.Raw(allow_none=True)
    category_id = fields.Raw(allow_none=True)
    due_date = fields.Raw(allow_none=True)
    tags = fields.Raw(allow_none=True)

    def __init__(self, *args, due_date_hint=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.due_date_hint = due_date_hint

    @post_load
    def finalize(self, data, **kwargs):
        if not self.partial or "title" in data:
            title = data.get("title")
            if not title:
                raise ValidationError("Título é obrigatório")
            if len(title) < 3:
                raise ValidationError("Título muito curto")
            if len(title) > 200:
                raise ValidationError("Título muito longo")

        if "status" in data and data["status"] is not None:
            if data["status"] not in TaskStatus.ALL:
                raise ValidationError("Status inválido")
        elif not self.partial:
            data["status"] = TaskStatus.PENDING

        if "priority" in data and data["priority"] is not None:
            try:
                priority = int(data["priority"])
            except (TypeError, ValueError):
                raise ValidationError("Prioridade deve ser entre 1 e 5")
            if priority < Task.PRIORITY_MIN or priority > Task.PRIORITY_MAX:
                raise ValidationError("Prioridade deve ser entre 1 e 5")
            data["priority"] = priority
        elif not self.partial:
            data["priority"] = 3

        if "due_date" in data:
            raw_due_date = data["due_date"]
            if raw_due_date:
                try:
                    data["due_date"] = datetime.strptime(raw_due_date, "%Y-%m-%d")
                except (TypeError, ValueError):
                    message = "Formato de data inválido. Use YYYY-MM-DD" if self.due_date_hint else "Formato de data inválido"
                    raise ValidationError(message)
            else:
                data["due_date"] = None

        if "tags" in data and data["tags"] is not None:
            tags = data["tags"]
            data["tags"] = ",".join(tags) if isinstance(tags, list) else tags

        if not self.partial:
            data.setdefault("description", "")

        return data
