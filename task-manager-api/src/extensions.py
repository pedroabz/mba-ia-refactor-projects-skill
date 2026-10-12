"""Framework extension objects.

These are module-level by design: Flask extensions are handles that get bound
to an app by `init_app` inside the factory, not shared mutable state. Keeping
them here is what lets a model import `db` without importing the application.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()

# In-process storage is fine for a single development server. A multi-worker
# deployment needs shared storage (Redis) or each worker counts separately.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """Turn on foreign-key enforcement for SQLite (T-11).

    SQLite defaults `PRAGMA foreign_keys` to OFF per connection, so the
    constraints the schema declares — including the ON DELETE clauses added
    for the category and user relationships — are ignored unless enabled here.
    A declared constraint that is never enforced is not a fix.
    """
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
