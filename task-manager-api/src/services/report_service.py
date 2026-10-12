"""Reporting logic that spans several entities.

These rules belonged to no single entity, so they live in a service rather
than on a model (LAY-02/LAY-03). The functions return plain values; rendering
them as JSON is the serializer's job.

Every aggregate is computed by the database. The old handlers loaded every
task row and counted in Python loops, and issued one query per user on top
(DAT-04, DAT-05).
"""
from datetime import timedelta

from src.models.category_model import Category
from src.models.task_model import PRIORITY_LABELS, Task
from src.models.user_model import User
from src.utils.clock import utcnow
from src.utils.numbers import percentage

#: Window used by the "recent activity" section of the summary report.
RECENT_ACTIVITY_WINDOW_DAYS = 7

#: Cap on the overdue list embedded in the summary. The old report embedded
#: every overdue task with no bound, so a large backlog became a single
#: unbounded JSON array (DAT-05).
MAX_EMBEDDED_OVERDUE = 100


def completion_rate(completed: int, total: int) -> float:
    """Share of a task set that is done. One owner; was written out 3 times."""
    return percentage(completed, total)


def task_stats() -> dict:
    """Totals behind GET /tasks/stats."""
    by_status = Task.count_by_status()
    total = Task.count_all()
    done = by_status.get("done", 0)
    return {
        "total": total,
        **by_status,
        "overdue": Task.count_overdue(),
        "completion_rate": completion_rate(done, total),
    }


def user_productivity() -> list[dict]:
    """Per-user totals and completion rate, from one grouped query."""
    stats = Task.completion_stats_by_user()
    rows = []
    for user in User.list_all(limit=User.count_all() or 1):
        total, completed = stats.get(user.id, (0, 0))
        rows.append({
            "user_id": user.id,
            "user_name": user.name,
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": completion_rate(completed, total),
        })
    return rows


def summary() -> dict:
    """Everything behind GET /reports/summary."""
    by_status = Task.count_by_status()
    by_priority = Task.count_by_priority()
    since = utcnow() - timedelta(days=RECENT_ACTIVITY_WINDOW_DAYS)

    return {
        "generated_at": utcnow(),
        "totals": {
            "tasks": Task.count_all(),
            "users": User.count_all(),
            "categories": Category.count_all(),
        },
        "by_status": by_status,
        # Labels come from the single priority scale on the model, so the
        # report and the domain can no longer disagree about what "high" means.
        "by_priority": {
            PRIORITY_LABELS[level]: by_priority.get(level, 0)
            for level in sorted(PRIORITY_LABELS)
        },
        "overdue_count": Task.count_overdue(),
        "overdue_tasks": Task.list_overdue(limit=MAX_EMBEDDED_OVERDUE),
        "created_recently": Task.count_created_since(since),
        "completed_recently": Task.count_completed_since(since),
        "user_productivity": user_productivity(),
    }


def for_user(user: User) -> dict:
    """Everything behind GET /reports/user/<id>.

    Loads the user's tasks once and derives every figure from that one set,
    using the model's own rules for overdue and high priority.
    """
    tasks = Task.for_user(user.id, limit=Task.count_for_user(user.id) or 1)
    counts = {status: 0 for status in ("done", "pending", "in_progress", "cancelled")}
    overdue = high_priority = 0

    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1
        if task.is_high_priority:
            high_priority += 1
        if task.is_overdue:
            overdue += 1

    total = len(tasks)
    return {
        "user": user,
        "total_tasks": total,
        **counts,
        "overdue": overdue,
        "high_priority": high_priority,
        "completion_rate": completion_rate(counts["done"], total),
    }
