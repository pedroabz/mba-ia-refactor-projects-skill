"""User entity: shape, credential handling, and data access for users."""
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from src.extensions import db
from src.utils.clock import utcnow

# --- domain constants (T-20) -------------------------------------------------
ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
VALID_ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)

#: Roles allowed to read other people's data and manage shared resources.
PRIVILEGED_ROLES = frozenset({ROLE_ADMIN, ROLE_MANAGER})

#: Unchanged from the original boundary check. The audit recommends raising
#: this; doing so would reject credentials the API currently accepts, so it is
#: left as an explicit operator decision rather than a silent contract change.
MIN_PASSWORD_LENGTH = 4

EMAIL_PATTERN = r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    # Renamed from `password`: the column holds a derived hash, and the old
    # name is what made including it in a serializer look harmless (SEC-02).
    password_hash = db.Column("password_hash", db.String(255), nullable=False)
    role = db.Column(db.String(50), default=ROLE_USER)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    # --- credentials (T-03) --------------------------------------------------

    def set_password(self, raw_password: str) -> None:
        """Store a salted PBKDF2 hash.

        Replaces unsalted MD5. Every write path goes through here, including
        the seed, so no path can reintroduce a bare digest.
        """
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Constant-time verification via the library, never `==`."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    # --- domain rules --------------------------------------------------------

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_privileged(self) -> bool:
        """May act on resources belonging to other users."""
        return self.role in PRIVILEGED_ROLES

    # --- data access ---------------------------------------------------------

    @classmethod
    def get_by_id(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def get_by_email(cls, email: str):
        return db.session.scalars(select(cls).where(cls.email == email)).first()

    @classmethod
    def email_taken_by_other(cls, email: str, user_id: int) -> bool:
        stmt = select(func.count()).select_from(cls).where(
            cls.email == email, cls.id != user_id
        )
        return (db.session.scalar(stmt) or 0) > 0

    @classmethod
    def list_all(cls, limit: int, offset: int = 0):
        stmt = select(cls).order_by(cls.id).limit(limit).offset(offset)
        return db.session.scalars(stmt).all()

    @classmethod
    def count_all(cls) -> int:
        return db.session.scalar(select(func.count()).select_from(cls)) or 0

    # --- persistence ---------------------------------------------------------

    def save(self) -> "User":
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self) -> None:
        """Delete the user; the tasks cascade at the database level (T-11)."""
        db.session.delete(self)
        db.session.commit()
