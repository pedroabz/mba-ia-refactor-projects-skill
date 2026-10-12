"""Model package.

Importing every model here guarantees all mappers are registered before
`db.create_all()` or a migration runs, regardless of which module the caller
imported first.
"""
from src.models.category_model import Category
from src.models.task_model import Task
from src.models.user_model import User

__all__ = ["Category", "Task", "User"]
