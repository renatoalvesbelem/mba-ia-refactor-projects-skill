from database import db
from models.base import utc_now


class TaskStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"

    ALL = (PENDING, IN_PROGRESS, DONE, CANCELLED)
    OPEN = (PENDING, IN_PROGRESS)


class Task(db.Model):
    __tablename__ = "tasks"

    PRIORITY_MIN = 1
    PRIORITY_MAX = 5
    SUMMARY_FIELDS = ("id", "title", "description", "status", "priority", "created_at", "due_date")

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=TaskStatus.PENDING)
    priority = db.Column(db.Integer, default=3)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", back_populates="tasks")
    category = db.relationship("Category", back_populates="tasks")

    def is_overdue(self):
        return bool(self.due_date and self.due_date < utc_now() and self.status in TaskStatus.OPEN)

    def tag_list(self):
        return self.tags.split(",") if self.tags else []

    def set_tags(self, tags):
        if isinstance(tags, list):
            self.tags = ",".join(tags)
        else:
            self.tags = tags

    def to_dict(self, include_user=False, include_category=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "tags": self.tag_list(),
            "overdue": self.is_overdue(),
        }
        if include_user:
            data["user_name"] = self.user.name if self.user else None
        if include_category:
            data["category_name"] = self.category.name if self.category else None
        return data

    def to_summary_dict(self):
        data = {field: getattr(self, field) for field in self.SUMMARY_FIELDS}
        data["created_at"] = str(data["created_at"])
        data["due_date"] = str(data["due_date"]) if data["due_date"] else None
        data["overdue"] = self.is_overdue()
        return data
