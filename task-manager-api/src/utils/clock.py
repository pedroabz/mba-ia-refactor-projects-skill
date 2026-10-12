"""Time source (T-24).

`datetime.utcnow()` is deprecated since Python 3.12 and appeared at 18 call
sites. This is the single replacement, so the next migration is a one-line
change and tests can patch one name.

It deliberately returns a **naive** UTC datetime rather than an aware one.
That is not an oversight: SQLite does not persist timezone offsets, so
`DateTime(timezone=True)` reads back naive values. Mixing those with an aware
`now()` raises `TypeError: can't compare offset-naive and offset-aware
datetimes` on every overdue comparison. Keeping the whole application naive-UTC
removes the deprecated call — which is the finding — while staying internally
consistent. Moving to aware datetimes end to end requires a backend that stores
offsets (PostgreSQL `timestamptz`); when that happens, change it here.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time, naive, matching how the columns are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
