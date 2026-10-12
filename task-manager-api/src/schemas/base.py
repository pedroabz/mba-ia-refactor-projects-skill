"""Schema loading helpers (T-15).

`marshmallow` was a declared dependency the project never imported, while the
handlers compared and cast request fields without type checks — so
`{"priority": "high"}` raised TypeError and became a 500 (API-03).

The update variant of each schema is derived from the create variant rather
than written again, which is what stops the drift where one path validates a
field and the other does not.
"""
from marshmallow import Schema, ValidationError

from src.middlewares.error_handler import BadRequest, ValidationFailed


def load_or_raise(schema: Schema, payload, *, field_order=()) -> dict:
    """Validate `payload` against `schema`, raising ValidationFailed on error.

    `field_order` preserves the order in which the original handlers reported
    problems, so the `error` message a client sees is the same one it saw
    before. Full field-level output is attached as `details`.
    """
    # An absent or empty body answers "Dados inválidos", as it always has.
    # This is the one truthiness check kept deliberately: it concerns the
    # whole payload, not a field value, so it cannot reject a legitimate 0.
    if not payload or not isinstance(payload, dict):
        raise BadRequest("Dados inválidos")
    try:
        return schema.load(payload)
    except ValidationError as err:
        raise ValidationFailed(
            message=_primary_message(err.messages, field_order),
            details=err.messages,
        ) from err


def _primary_message(messages, field_order) -> str:
    """Pick the message to surface as `error`, honouring the original order."""
    if not isinstance(messages, dict):
        return "Dados inválidos"
    for field in field_order:
        if field in messages:
            return _first_string(messages[field])
    for value in messages.values():
        text = _first_string(value)
        if text:
            return text
    return "Dados inválidos"


def _first_string(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and value:
        return _first_string(value[0])
    if isinstance(value, dict):
        for nested in value.values():
            text = _first_string(nested)
            if text:
                return text
    return ""
