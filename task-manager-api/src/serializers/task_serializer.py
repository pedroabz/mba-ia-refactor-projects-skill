"""Task response shapes.

Serialization moved out of the models (LAY-03): persistence no longer decides
the API contract. There is one canonical task shape, used by every endpoint
that returns a task, because the old code had four divergent ones (API-05) —
`overdue` was present in two of them and absent in the other two, so a client
could not tell "not overdue" from "not reported".
"""
from src.models.task_model import Task
from src.serializers.common import format_datetime


def task_dict(task: Task) -> dict:
    """The canonical task representation."""
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "user_id": task.user_id,
        "category_id": task.category_id,
        "created_at": format_datetime(task.created_at),
        "updated_at": format_datetime(task.updated_at),
        "due_date": format_datetime(task.due_date),
        "tags": task.tag_list,
        "overdue": task.is_overdue,
        # Relations are eager-loaded by the model, so reading them here costs
        # no extra query (T-12).
        "user_name": task.user.name if task.user else None,
        "category_name": task.category.name if task.category else None,
    }


def task_list(tasks) -> list[dict]:
    return [task_dict(task) for task in tasks]


def overdue_entry(task: Task) -> dict:
    """The compact shape the summary report embeds for each overdue task."""
    return {
        "id": task.id,
        "title": task.title,
        "due_date": format_datetime(task.due_date),
        "days_overdue": task.days_overdue,
    }
