from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models.base import utc_now


class UserRole:
    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"

    ALL = (USER, ADMIN, MANAGER)


class User(db.Model):
    __tablename__ = "users"

    PUBLIC_FIELDS = ("id", "name", "email", "role", "active", "created_at")

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=UserRole.USER)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    tasks = db.relationship("Task", back_populates="user")

    def to_dict(self, include_task_count=False):
        data = {field: getattr(self, field) for field in self.PUBLIC_FIELDS}
        data["created_at"] = str(data["created_at"])
        if include_task_count:
            data["task_count"] = len(self.tasks)
        return data

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)
