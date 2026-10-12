"""User use cases."""
from flask import jsonify, request

from src.config.logging_config import get_logger
from src.controllers.pagination import page_params, paginated
from src.middlewares.auth import current_user
from src.middlewares.error_handler import Conflict, Forbidden, NotFound
from src.models.task_model import Task
from src.models.user_model import User
from src.schemas.base import load_or_raise
from src.schemas.user_schema import FIELD_ORDER, UserCreateSchema, UserUpdateSchema
from src.serializers.task_serializer import task_list
from src.serializers.user_serializer import user_dict, user_list, user_with_tasks

logger = get_logger(__name__)


def _require_user(user_id: int) -> User:
    user = User.get_by_id(user_id)
    if user is None:
        raise NotFound("Usuário não encontrado")
    return user


def list_users():
    limit, offset = page_params()
    users = User.list_all(limit=limit, offset=offset)
    # One grouped query for all task counts, where the old handler read
    # `len(u.tasks)` per row and lazy-loaded every task (DAT-04).
    counts = {uid: total for uid, (total, _done)
              in Task.completion_stats_by_user().items()}
    return paginated(user_list(users, counts), User.count_all())


def get_user(user_id):
    user = _require_user(user_id)
    tasks = Task.for_user(user_id, limit=Task.count_for_user(user_id) or 1)
    return jsonify(user_with_tasks(user, tasks)), 200


def create_user():
    data = load_or_raise(
        UserCreateSchema(), request.get_json(silent=True), field_order=FIELD_ORDER
    )
    if User.get_by_email(data["email"]) is not None:
        raise Conflict("Email já cadastrado")

    user = User()
    user.name = data["name"]
    user.email = data["email"]
    user.set_password(data["password"])
    user.role = data["role"]
    user.save()

    logger.info("user created id=%s", user.id)
    return jsonify(user_dict(user)), 201


def update_user(user_id):
    user = _require_user(user_id)
    data = load_or_raise(
        UserUpdateSchema(), request.get_json(silent=True), field_order=FIELD_ORDER
    )

    if "email" in data and User.email_taken_by_other(data["email"], user_id):
        raise Conflict("Email já cadastrado")

    # Privilege escalation was previously open: any caller could set any
    # account's role, including their own, to admin (SEC-05).
    if "role" in data and data["role"] != user.role:
        caller = current_user()
        if caller is None or not caller.is_admin:
            raise Forbidden("Apenas administradores podem alterar o papel de um usuário")

    if "name" in data:
        user.name = data["name"]
    if "email" in data:
        user.email = data["email"]
    if "password" in data:
        user.set_password(data["password"])
    if "role" in data:
        user.role = data["role"]
    if "active" in data:
        user.active = data["active"]

    user.save()
    logger.info("user updated id=%s", user.id)
    return jsonify(user_dict(user)), 200


def delete_user(user_id):
    user = _require_user(user_id)
    # The user's tasks go with them, by the ON DELETE CASCADE declared on the
    # foreign key. The old handler deleted them by hand in the same session.
    user.delete()
    logger.info("user deleted id=%s", user_id)
    return jsonify({"message": "Usuário deletado com sucesso"}), 200


def get_user_tasks(user_id):
    _require_user(user_id)
    limit, offset = page_params()
    tasks = Task.for_user(user_id, limit=limit, offset=offset)
    return paginated(task_list(tasks), Task.count_for_user(user_id))
