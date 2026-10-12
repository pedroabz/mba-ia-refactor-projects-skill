"""Pagination parameters read from the query string (T-13).

Every collection endpoint previously issued `.all()` with no bound. The limit
is clamped server-side: a client-supplied page size is a request, not an
authorization.

The response stays a bare JSON array so existing clients are unaffected; the
total goes in an `X-Total-Count` header instead of wrapping the body in an
envelope.
"""
from flask import current_app, request

from src.middlewares.error_handler import BadRequest


def page_params() -> tuple[int, int]:
    settings = current_app.config["SETTINGS"]
    limit = int_arg("limit", settings.DEFAULT_PAGE_SIZE)
    offset = int_arg("offset", 0)
    limit = min(max(limit, 1), settings.MAX_PAGE_SIZE)
    return limit, max(offset, 0)


def int_arg(name: str, default: int | None = None) -> int | None:
    """Read an integer query parameter, rejecting a malformed one as a 400.

    The old handlers used a bare `int()`, so `?priority=abc` raised ValueError
    and surfaced as a 500.
    """
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise BadRequest(f"Parâmetro '{name}' deve ser um número inteiro") from None


def paginated(payload, total: int):
    """Attach the collection total as a header."""
    from flask import jsonify

    response = jsonify(payload)
    response.headers["X-Total-Count"] = str(total)
    return response, 200
