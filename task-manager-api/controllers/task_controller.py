import logging

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from controllers.schema_utils import load_or_raise
from database import db
from middlewares.error_handler import NotFoundError, ValidationError
from models.base import utc_now
from models.category import Category
from models.task import Task, TaskStatus
from models.user import User
from schemas.task_schema import TaskSchema

logger = logging.getLogger(__name__)


class TaskController:
    def list_all(self):
        tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
        return [task.to_dict(include_user=True, include_category=True) for task in tasks]

    def get(self, task_id):
        task = self._require_task(task_id)
        return task.to_dict()

    def create(self, payload):
        data = load_or_raise(TaskSchema(due_date_hint=True), payload)
        self._check_user_exists(data.get("user_id"))
        self._check_category_exists(data.get("category_id"))
        task = Task(**data)
        db.session.add(task)
        db.session.commit()
        logger.info("task created id=%s", task.id)
        return task

    def update(self, task_id, payload):
        task = self._require_task(task_id)
        data = load_or_raise(TaskSchema(partial=True, due_date_hint=False), payload)
        if "user_id" in data:
            self._check_user_exists(data["user_id"])
        if "category_id" in data:
            self._check_category_exists(data["category_id"])
        for field, value in data.items():
            setattr(task, field, value)
        task.updated_at = utc_now()
        db.session.commit()
        logger.info("task updated id=%s", task.id)
        return task

    def delete(self, task_id):
        task = self._require_task(task_id)
        db.session.delete(task)
        db.session.commit()
        logger.info("task deleted id=%s", task_id)

    def search(self, query, status, priority, user_id):
        tasks = Task.query
        if query:
            tasks = tasks.filter(db.or_(Task.title.like(f"%{query}%"), Task.description.like(f"%{query}%")))
        if status:
            tasks = tasks.filter(Task.status == status)
        if priority:
            try:
                tasks = tasks.filter(Task.priority == int(priority))
            except ValueError:
                raise ValidationError("Prioridade inválida")
        if user_id:
            try:
                tasks = tasks.filter(Task.user_id == int(user_id))
            except ValueError:
                raise ValidationError("Usuário inválido")
        return [task.to_dict() for task in tasks.all()]

    def stats(self):
        rows = db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
        counts = {status: 0 for status in TaskStatus.ALL}
        counts.update(dict(rows))
        total = sum(counts.values())
        overdue_count = Task.query.filter(
            Task.due_date.isnot(None),
            Task.due_date < utc_now(),
            Task.status.in_(TaskStatus.OPEN),
        ).count()
        done = counts[TaskStatus.DONE]
        return {
            "total": total,
            "pending": counts[TaskStatus.PENDING],
            "in_progress": counts[TaskStatus.IN_PROGRESS],
            "done": done,
            "cancelled": counts[TaskStatus.CANCELLED],
            "overdue": overdue_count,
            "completion_rate": round((done / total) * 100, 2) if total > 0 else 0,
        }

    def _require_task(self, task_id):
        task = db.session.get(Task, task_id)
        if not task:
            raise NotFoundError("Task não encontrada")
        return task

    def _check_user_exists(self, user_id):
        if user_id and not db.session.get(User, user_id):
            raise NotFoundError("Usuário não encontrado")

    def _check_category_exists(self, category_id):
        if category_id and not db.session.get(Category, category_id):
            raise NotFoundError("Categoria não encontrada")
