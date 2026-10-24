from sqlalchemy import func

from database import db
from models.base import utc_now


class Category(db.Model):
    __tablename__ = "categories"

    PUBLIC_FIELDS = ("id", "name", "description", "color", "created_at")
    DEFAULT_COLOR = "#000000"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utc_now)

    tasks = db.relationship("Task", back_populates="category")

    def to_dict(self, task_count=None):
        data = {field: getattr(self, field) for field in self.PUBLIC_FIELDS}
        data["created_at"] = str(data["created_at"])
        if task_count is not None:
            data["task_count"] = task_count
        return data

    @classmethod
    def list_with_task_counts(cls):
        from models.task import Task

        rows = (
            db.session.query(cls, func.count(Task.id))
            .outerjoin(Task, Task.category_id == cls.id)
            .group_by(cls.id)
            .order_by(cls.id)
            .all()
        )
        return rows
