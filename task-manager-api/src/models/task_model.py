"""Task entity: shape, invariants, and data access for tasks.

Owns the domain rules that were previously copy-pasted into route handlers —
most importantly the overdue rule, which existed in six places while the
`is_overdue` method here was never called (QUA-01).

Returns entities and values. It never shapes an HTTP response and never
imports Flask's request object; serialization lives in src/serializers.
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.extensions import db
from src.utils.clock import utcnow

# --- domain constants (T-20) -------------------------------------------------
# These were inline literals at each use site, with an unused copy in the old
# utils/helpers.py. The entity that the rules describe owns them now.
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"

VALID_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED)

#: A task in one of these states can no longer be late.
TERMINAL_STATUSES = frozenset({STATUS_DONE, STATUS_CANCELLED})

MIN_PRIORITY, MAX_PRIORITY = 1, 5
DEFAULT_PRIORITY = 3

#: The priority scale, named once. The old code encoded it twice and the two
#: encodings disagreed: a label map called 2 "high", while a separate threshold
#: counted 1 and 2 together as "high priority".
PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}
#: Upper bound (inclusive) of what counts as high priority for reporting.
HIGH_PRIORITY_MAX = 2

MIN_TITLE_LENGTH, MAX_TITLE_LENGTH = 3, 200
TAG_SEPARATOR = ","


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(MAX_TITLE_LENGTH), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=STATUS_PENDING)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)

    # Delete policy is declared here rather than inherited from ORM defaults
    # (T-11). Deleting a user removes their tasks; deleting a category leaves
    # the tasks and clears the classification.
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship(
        "User",
        backref=db.backref(
            "tasks",
            # Matches the behaviour the old handler implemented by hand: a
            # user's tasks go with the user. Not delete-orphan, because
            # clearing task.user_id must null the column, not delete the task.
            cascade="save-update, merge, delete",
            passive_deletes=True,
        ),
    )
    category = db.relationship("Category", backref=db.backref("tasks"))

    # --- domain rules --------------------------------------------------------

    @property
    def is_overdue(self) -> bool:
        """Single owner of the overdue rule (QUA-01).

        Was reimplemented as a four-level nested conditional in six places
        across three route modules while this method went uncalled.
        """
        if self.due_date is None or self.status in TERMINAL_STATUSES:
            return False
        return self.due_date < utcnow()

    @property
    def days_overdue(self) -> int:
        """Whole days past the due date, or 0 when not overdue."""
        if not self.is_overdue:
            return 0
        return (utcnow() - self.due_date).days

    @property
    def is_high_priority(self) -> bool:
        return self.priority is not None and self.priority <= HIGH_PRIORITY_MAX

    @property
    def tag_list(self) -> list[str]:
        return self.tags.split(TAG_SEPARATOR) if self.tags else []

    @tag_list.setter
    def tag_list(self, values) -> None:
        if values is None:
            self.tags = None
        elif isinstance(values, (list, tuple)):
            self.tags = TAG_SEPARATOR.join(str(v) for v in values)
        else:
            self.tags = values

    # --- data access ---------------------------------------------------------
    # Queries live with the entity they load, so no controller touches the
    # session directly (LAY-05).

    @staticmethod
    def _with_relations(stmt):
        """Eager-load user and category: 3 queries instead of 1 + 2N (T-12)."""
        return stmt.options(selectinload(Task.user), selectinload(Task.category))

    @classmethod
    def get_by_id(cls, task_id):
        # db.session.get replaces the legacy Query.get(), which emits
        # LegacyAPIWarning under SQLAlchemy 2.x (DEP-01).
        return db.session.get(cls, task_id)

    @classmethod
    def list_all(cls, limit: int, offset: int = 0):
        stmt = cls._with_relations(
            select(cls).order_by(cls.id).limit(limit).offset(offset)
        )
        return db.session.scalars(stmt).all()

    @classmethod
    def search(cls, term=None, status=None, priority=None, user_id=None,
               limit: int = 50, offset: int = 0):
        stmt = select(cls)
        if term:
            # The f-string builds the LIKE pattern; the driver still binds it
            # as a parameter, so this is not string-assembled SQL.
            pattern = f"%{term}%"
            stmt = stmt.where(
                or_(cls.title.like(pattern), cls.description.like(pattern))
            )
        if status:
            stmt = stmt.where(cls.status == status)
        if priority is not None:
            stmt = stmt.where(cls.priority == priority)
        if user_id is not None:
            stmt = stmt.where(cls.user_id == user_id)
        stmt = cls._with_relations(stmt.order_by(cls.id).limit(limit).offset(offset))
        return db.session.scalars(stmt).all()

    @classmethod
    def for_user(cls, user_id: int, limit: int, offset: int = 0):
        stmt = cls._with_relations(
            select(cls)
            .where(cls.user_id == user_id)
            .order_by(cls.id)
            .limit(limit)
            .offset(offset)
        )
        return db.session.scalars(stmt).all()

    @classmethod
    def count_all(cls) -> int:
        return db.session.scalar(select(func.count()).select_from(cls)) or 0

    @classmethod
    def count_for_user(cls, user_id: int) -> int:
        return db.session.scalar(
            select(func.count()).select_from(cls).where(cls.user_id == user_id)
        ) or 0

    @classmethod
    def count_matching(cls, term=None, status=None, priority=None, user_id=None) -> int:
        stmt = select(func.count()).select_from(cls)
        if term:
            pattern = f"%{term}%"
            stmt = stmt.where(
                or_(cls.title.like(pattern), cls.description.like(pattern))
            )
        if status:
            stmt = stmt.where(cls.status == status)
        if priority is not None:
            stmt = stmt.where(cls.priority == priority)
        if user_id is not None:
            stmt = stmt.where(cls.user_id == user_id)
        return db.session.scalar(stmt) or 0

    @classmethod
    def count_by_status(cls) -> dict[str, int]:
        """One grouped query, replacing four separate counts (T-12)."""
        rows = db.session.execute(
            select(cls.status, func.count()).group_by(cls.status)
        ).all()
        counts = {status: 0 for status in VALID_STATUSES}
        for status, total in rows:
            counts[status] = total
        return counts

    @classmethod
    def count_by_priority(cls) -> dict[int, int]:
        """One grouped query, replacing the five p1..p5 counts (T-12)."""
        rows = db.session.execute(
            select(cls.priority, func.count()).group_by(cls.priority)
        ).all()
        counts = {level: 0 for level in PRIORITY_LABELS}
        for level, total in rows:
            if level in counts:
                counts[level] = total
        return counts

    @classmethod
    def _overdue_where(cls, now):
        return (
            cls.due_date.is_not(None),
            cls.due_date < now,
            cls.status.not_in(tuple(TERMINAL_STATUSES)),
        )

    @classmethod
    def count_overdue(cls) -> int:
        """Counted in the database, not by loading every row into Python."""
        return db.session.scalar(
            select(func.count()).select_from(cls).where(*cls._overdue_where(utcnow()))
        ) or 0

    @classmethod
    def list_overdue(cls, limit: int, offset: int = 0):
        stmt = (
            select(cls)
            .where(*cls._overdue_where(utcnow()))
            .order_by(cls.due_date)
            .limit(limit)
            .offset(offset)
        )
        return db.session.scalars(stmt).all()

    @classmethod
    def count_created_since(cls, moment) -> int:
        return db.session.scalar(
            select(func.count()).select_from(cls).where(cls.created_at >= moment)
        ) or 0

    @classmethod
    def count_completed_since(cls, moment) -> int:
        return db.session.scalar(
            select(func.count())
            .select_from(cls)
            .where(cls.status == STATUS_DONE, cls.updated_at >= moment)
        ) or 0

    @classmethod
    def completion_stats_by_user(cls) -> dict[int, tuple[int, int]]:
        """(total, completed) per user id in one grouped query.

        Replaces a per-user `filter_by(...).all()` inside a loop that also
        loaded every full task row to count two statuses (DAT-04).
        """
        rows = db.session.execute(
            select(
                cls.user_id,
                func.count(),
                func.sum(func.cast(cls.status == STATUS_DONE, db.Integer)),
            )
            .where(cls.user_id.is_not(None))
            .group_by(cls.user_id)
        ).all()
        return {uid: (total, int(done or 0)) for uid, total, done in rows}

    @classmethod
    def count_by_category(cls) -> dict[int, int]:
        rows = db.session.execute(
            select(cls.category_id, func.count())
            .where(cls.category_id.is_not(None))
            .group_by(cls.category_id)
        ).all()
        return {cid: total for cid, total in rows}

    # --- persistence ---------------------------------------------------------

    def save(self) -> "Task":
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self) -> None:
        db.session.delete(self)
        db.session.commit()
