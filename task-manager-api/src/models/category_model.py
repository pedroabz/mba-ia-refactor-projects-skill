"""Category entity: shape and data access for categories."""
import re

from sqlalchemy import func, select

from src.extensions import db
from src.utils.clock import utcnow

DEFAULT_COLOR = "#000000"
#: A seven-character hex colour, which is what the column width allows.
COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"
MIN_NAME_LENGTH, MAX_NAME_LENGTH = 1, 100


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(MAX_NAME_LENGTH), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utcnow)

    @staticmethod
    def is_valid_color(value: str) -> bool:
        """Salvaged from the dead utils/helpers.is_valid_color, which checked
        only length and a leading '#'. This also checks the digits are hex."""
        return bool(value) and re.match(COLOR_PATTERN, value) is not None

    # --- data access ---------------------------------------------------------

    @classmethod
    def get_by_id(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def list_all(cls):
        """Unpaginated on purpose: a classification table is bounded by design,
        unlike tasks and users. Noted so it is not "fixed" later."""
        return db.session.scalars(select(cls).order_by(cls.id)).all()

    @classmethod
    def count_all(cls) -> int:
        return db.session.scalar(select(func.count()).select_from(cls)) or 0

    # --- persistence ---------------------------------------------------------

    def save(self) -> "Category":
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self) -> None:
        """Delete the category; referencing tasks have category_id set to NULL
        by the foreign key's ON DELETE SET NULL clause (T-11)."""
        db.session.delete(self)
        db.session.commit()
