"""Task use cases.

Each function reads the request, validates it, calls the domain and chooses a
status code. No ORM query, no domain rule, no try/except: queries live on the
model, rules live on the entity, and errors are raised for the centralized
handler to answer.
"""
from flask import jsonify, request

from src.config.logging_config import get_logger
from src.controllers.pagination import int_arg, page_params, paginated
from src.middlewares.error_handler import NotFound
from src.models.category_model import Category
from src.models.task_model import Task
from src.models.user_model import User
from src.schemas.base import load_or_raise
from src.schemas.task_schema import (
    FIELD_ORDER,
    TaskCreateSchema,
    TaskUpdateSchema,
)
from src.serializers import report_serializer
from src.serializers.task_serializer import task_dict, task_list
from src.services import report_service

logger = get_logger(__name__)


def _require_task(task_id: int) -> Task:
    task = Task.get_by_id(task_id)
    if task is None:
        raise NotFound("Task não encontrada")
    return task


def _resolve_references(data: dict) -> None:
    """Confirm referenced user and category exist, when supplied."""
    if data.get("user_id") is not None and User.get_by_id(data["user_id"]) is None:
        raise NotFound("Usuário não encontrado")
    if data.get("category_id") is not None and Category.get_by_id(data["category_id"]) is None:
        raise NotFound("Categoria não encontrada")


def _assign(task: Task, data: dict) -> None:
    """Copy validated fields onto the entity, skipping absent keys."""
    for field in ("title", "description", "status", "priority",
                  "user_id", "category_id", "due_date"):
        if field in data:
            setattr(task, field, data[field])
    if "tags" in data:
        task.tag_list = data["tags"]


def list_tasks():
    limit, offset = page_params()
    tasks = Task.list_all(limit=limit, offset=offset)
    return paginated(task_list(tasks), Task.count_all())


def get_task(task_id):
    return jsonify(task_dict(_require_task(task_id))), 200


def create_task():
    data = load_or_raise(
        TaskCreateSchema(), request.get_json(silent=True), field_order=FIELD_ORDER
    )
    _resolve_references(data)

    task = Task()
    _assign(task, data)
    task.save()

    logger.info("task created id=%s", task.id)
    return jsonify(task_dict(task)), 201


def update_task(task_id):
    task = _require_task(task_id)
    data = load_or_raise(
        TaskUpdateSchema(), request.get_json(silent=True), field_order=FIELD_ORDER
    )
    _resolve_references(data)

    _assign(task, data)
    task.save()

    logger.info("task updated id=%s", task.id)
    return jsonify(task_dict(task)), 200


def delete_task(task_id):
    task = _require_task(task_id)
    task.delete()
    logger.info("task deleted id=%s", task_id)
    return jsonify({"message": "Task deletada com sucesso"}), 200


def search_tasks():
    limit, offset = page_params()
    term = request.args.get("q") or None
    status = request.args.get("status") or None
    # The old handler cast these with a bare `int()`, so `?priority=abc`
    # raised ValueError and became a 500. Rejecting it as a client error is
    # the fix; silently ignoring the filter would be worse than either.
    priority = int_arg("priority")
    user_id = int_arg("user_id")

    tasks = Task.search(
        term=term, status=status, priority=priority, user_id=user_id,
        limit=limit, offset=offset,
    )
    total = Task.count_matching(
        term=term, status=status, priority=priority, user_id=user_id
    )
    return paginated(task_list(tasks), total)


def task_stats():
    return jsonify(report_serializer.task_stats(report_service.task_stats())), 200
