"""Category response shapes."""
from src.models.category_model import Category
from src.serializers.common import format_datetime


def category_dict(category: Category, task_count: int | None = None) -> dict:
    data = {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "created_at": format_datetime(category.created_at),
    }
    if task_count is not None:
        data["task_count"] = task_count
    return data


def category_list(categories, task_counts: dict[int, int]) -> list[dict]:
    """`task_counts` comes from one grouped query, not a count per row."""
    return [category_dict(c, task_counts.get(c.id, 0)) for c in categories]
