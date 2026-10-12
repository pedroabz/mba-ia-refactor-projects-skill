"""Report response shapes.

Renders the values the report service computed. The nesting below is the
response contract and is unchanged from the original handlers; what changed is
that no aggregation happens here.
"""
from src.serializers.common import format_datetime
from src.serializers.task_serializer import overdue_entry


def summary(data: dict) -> dict:
    return {
        "generated_at": format_datetime(data["generated_at"]),
        "overview": {
            "total_tasks": data["totals"]["tasks"],
            "total_users": data["totals"]["users"],
            "total_categories": data["totals"]["categories"],
        },
        "tasks_by_status": {
            "pending": data["by_status"]["pending"],
            "in_progress": data["by_status"]["in_progress"],
            "done": data["by_status"]["done"],
            "cancelled": data["by_status"]["cancelled"],
        },
        "tasks_by_priority": data["by_priority"],
        "overdue": {
            "count": data["overdue_count"],
            "tasks": [overdue_entry(task) for task in data["overdue_tasks"]],
        },
        "recent_activity": {
            "tasks_created_last_7_days": data["created_recently"],
            "tasks_completed_last_7_days": data["completed_recently"],
        },
        "user_productivity": data["user_productivity"],
    }


def user_report(data: dict) -> dict:
    user = data["user"]
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "statistics": {
            "total_tasks": data["total_tasks"],
            "done": data["done"],
            "pending": data["pending"],
            "in_progress": data["in_progress"],
            "cancelled": data["cancelled"],
            "overdue": data["overdue"],
            "high_priority": data["high_priority"],
            "completion_rate": data["completion_rate"],
        },
    }


def task_stats(data: dict) -> dict:
    return {
        "total": data["total"],
        "pending": data["pending"],
        "in_progress": data["in_progress"],
        "done": data["done"],
        "cancelled": data["cancelled"],
        "overdue": data["overdue"],
        "completion_rate": data["completion_rate"],
    }
