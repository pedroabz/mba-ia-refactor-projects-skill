"""User response shapes.

The credential field is absent from every shape here (T-04/SEC-02). The old
`User.to_dict()` included the password hash and four endpoints returned it;
because the leak lived in one serializer, so does the fix.
"""
from src.models.user_model import User
from src.serializers.common import format_datetime
from src.serializers.task_serializer import task_list


def user_dict(user: User, task_count: int | None = None) -> dict:
    """The canonical public user representation. Never includes credentials."""
    data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": format_datetime(user.created_at),
    }
    if task_count is not None:
        data["task_count"] = task_count
    return data


def user_list(users, task_counts: dict[int, int]) -> list[dict]:
    """`task_counts` comes from one grouped query rather than a lazy-loaded
    relation per row (DAT-04)."""
    return [user_dict(user, task_counts.get(user.id, 0)) for user in users]


def user_with_tasks(user: User, tasks) -> dict:
    data = user_dict(user)
    data["tasks"] = task_list(tasks)
    return data


def login_result(user: User, token: str) -> dict:
    return {
        "message": "Login realizado com sucesso",
        "user": user_dict(user),
        "token": token,
    }
