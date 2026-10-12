"""Category use cases."""
from flask import jsonify, request

from src.config.logging_config import get_logger
from src.middlewares.error_handler import NotFound
from src.models.category_model import Category
from src.models.task_model import Task
from src.schemas.base import load_or_raise
from src.schemas.category_schema import (
    FIELD_ORDER,
    CategoryCreateSchema,
    CategoryUpdateSchema,
)
from src.serializers.category_serializer import category_dict, category_list

logger = get_logger(__name__)


def _require_category(cat_id: int) -> Category:
    category = Category.get_by_id(cat_id)
    if category is None:
        raise NotFound("Categoria não encontrada")
    return category


def list_categories():
    categories = Category.list_all()
    # One grouped query, where the old handler ran a count per category.
    counts = Task.count_by_category()
    return jsonify(category_list(categories, counts)), 200


def create_category():
    data = load_or_raise(
        CategoryCreateSchema(), request.get_json(silent=True), field_order=FIELD_ORDER
    )
    category = Category()
    category.name = data["name"]
    category.description = data["description"]
    category.color = data["color"]
    category.save()

    logger.info("category created id=%s", category.id)
    return jsonify(category_dict(category)), 201


def update_category(cat_id):
    category = _require_category(cat_id)
    data = load_or_raise(
        CategoryUpdateSchema(), request.get_json(silent=True), field_order=FIELD_ORDER
    )
    for field in ("name", "description", "color"):
        if field in data:
            setattr(category, field, data[field])
    category.save()

    logger.info("category updated id=%s", category.id)
    return jsonify(category_dict(category)), 200


def delete_category(cat_id):
    category = _require_category(cat_id)
    # Tasks keep their row and have category_id cleared, by the SET NULL
    # declared on the foreign key rather than by ORM default behaviour (T-11).
    category.delete()
    logger.info("category deleted id=%s", cat_id)
    return jsonify({"message": "Categoria deletada"}), 200
