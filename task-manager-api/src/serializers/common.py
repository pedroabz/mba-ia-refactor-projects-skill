"""Shared formatting for response payloads."""


def format_datetime(value) -> str | None:
    """Render a datetime the way the API has always rendered it.

    Kept as `str(value)` rather than switching to ISO-8601 with a `T`
    separator: changing it would alter every timestamp in every response for
    no functional gain. Centralized here so the decision has one owner.
    """
    return str(value) if value is not None else None
