from datetime import timedelta

from sqlalchemy import func

from database import db
from middlewares.error_handler import NotFoundError
from models.base import utc_now
from models.category import Category
from models.task import Task, TaskStatus
from models.user import User

PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}


class ReportController:
    def summary(self):
        total_tasks = Task.query.count()
        total_users = User.query.count()
        total_categories = Category.query.count()

        status_rows = db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
        status_counts = {status: 0 for status in TaskStatus.ALL}
        status_counts.update(dict(status_rows))

        priority_rows = db.session.query(Task.priority, func.count(Task.id)).group_by(Task.priority).all()
        priority_counts = {priority: 0 for priority in range(1, 6)}
        priority_counts.update(dict(priority_rows))

        now = utc_now()
        overdue_tasks = Task.query.filter(
            Task.due_date.isnot(None),
            Task.due_date < now,
            Task.status.in_(TaskStatus.OPEN),
        ).all()
        overdue_list = [
            {
                "id": task.id,
                "title": task.title,
                "due_date": str(task.due_date),
                "days_overdue": (now - task.due_date).days,
            }
            for task in overdue_tasks
        ]

        seven_days_ago = now - timedelta(days=7)
        recent_tasks = Task.query.filter(Task.created_at >= seven_days_ago).count()
        recent_done = Task.query.filter(
            Task.status == TaskStatus.DONE,
            Task.updated_at >= seven_days_ago,
        ).count()

        user_task_rows = (
            db.session.query(Task.user_id, Task.status, func.count(Task.id))
            .group_by(Task.user_id, Task.status)
            .all()
        )
        stats_by_user = {}
        for user_id, status, count in user_task_rows:
            if user_id is None:
                continue
            entry = stats_by_user.setdefault(user_id, {"total": 0, "done": 0})
            entry["total"] += count
            if status == TaskStatus.DONE:
                entry["done"] += count

        user_stats = []
        for user in User.query.all():
            entry = stats_by_user.get(user.id, {"total": 0, "done": 0})
            total = entry["total"]
            completed = entry["done"]
            user_stats.append(
                {
                    "user_id": user.id,
                    "user_name": user.name,
                    "total_tasks": total,
                    "completed_tasks": completed,
                    "completion_rate": round((completed / total) * 100, 2) if total > 0 else 0,
                }
            )

        return {
            "generated_at": str(now),
            "overview": {
                "total_tasks": total_tasks,
                "total_users": total_users,
                "total_categories": total_categories,
            },
            "tasks_by_status": {
                "pending": status_counts[TaskStatus.PENDING],
                "in_progress": status_counts[TaskStatus.IN_PROGRESS],
                "done": status_counts[TaskStatus.DONE],
                "cancelled": status_counts[TaskStatus.CANCELLED],
            },
            "tasks_by_priority": {
                PRIORITY_LABELS[priority]: count for priority, count in priority_counts.items()
            },
            "overdue": {
                "count": len(overdue_list),
                "tasks": overdue_list,
            },
            "recent_activity": {
                "tasks_created_last_7_days": recent_tasks,
                "tasks_completed_last_7_days": recent_done,
            },
            "user_productivity": user_stats,
        }

    def user_report(self, user_id):
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError("Usuário não encontrado")

        total = Task.query.filter_by(user_id=user_id).count()
        status_rows = (
            db.session.query(Task.status, func.count(Task.id))
            .filter(Task.user_id == user_id)
            .group_by(Task.status)
            .all()
        )
        status_counts = {status: 0 for status in TaskStatus.ALL}
        status_counts.update(dict(status_rows))

        overdue = Task.query.filter(
            Task.user_id == user_id,
            Task.due_date.isnot(None),
            Task.due_date < utc_now(),
            Task.status.in_(TaskStatus.OPEN),
        ).count()
        high_priority = Task.query.filter(Task.user_id == user_id, Task.priority <= 2).count()
        done = status_counts[TaskStatus.DONE]

        return {
            "user": {"id": user.id, "name": user.name, "email": user.email},
            "statistics": {
                "total_tasks": total,
                "done": done,
                "pending": status_counts[TaskStatus.PENDING],
                "in_progress": status_counts[TaskStatus.IN_PROGRESS],
                "cancelled": status_counts[TaskStatus.CANCELLED],
                "overdue": overdue,
                "high_priority": high_priority,
                "completion_rate": round((done / total) * 100, 2) if total > 0 else 0,
            },
        }
