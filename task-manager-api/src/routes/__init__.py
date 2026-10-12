"""Route package: the application's entry surface.

`ALL_BLUEPRINTS` is the single list the composition root registers, so adding
an entry surface means touching this file rather than the factory.
"""
from src.routes.auth_routes import auth_bp
from src.routes.category_routes import category_bp
from src.routes.meta_routes import meta_bp
from src.routes.report_routes import report_bp
from src.routes.task_routes import task_bp
from src.routes.user_routes import user_bp

ALL_BLUEPRINTS = (meta_bp, auth_bp, task_bp, user_bp, category_bp, report_bp)

__all__ = ["ALL_BLUEPRINTS"]
