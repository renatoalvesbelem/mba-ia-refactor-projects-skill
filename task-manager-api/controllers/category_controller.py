import logging

from controllers.schema_utils import load_or_raise
from database import db
from middlewares.error_handler import NotFoundError
from models.category import Category
from schemas.category_schema import CategorySchema

logger = logging.getLogger(__name__)


class CategoryController:
    def list_all(self):
        rows = Category.list_with_task_counts()
        return [category.to_dict(task_count=count) for category, count in rows]

    def create(self, payload):
        data = load_or_raise(CategorySchema(), payload)
        category = Category(**data)
        db.session.add(category)
        db.session.commit()
        logger.info("category created id=%s", category.id)
        return category

    def update(self, category_id, payload):
        category = self._require_category(category_id)
        data = load_or_raise(CategorySchema(partial=True), payload)
        for field, value in data.items():
            setattr(category, field, value)
        db.session.commit()
        logger.info("category updated id=%s", category.id)
        return category

    def delete(self, category_id):
        category = self._require_category(category_id)
        db.session.delete(category)
        db.session.commit()
        logger.info("category deleted id=%s", category_id)

    def _require_category(self, category_id):
        category = db.session.get(Category, category_id)
        if not category:
            raise NotFoundError("Categoria não encontrada")
        return category
