"""Task request schemas.

Messages are the ones the API returned before, so the `error` field of a 400 is
unchanged; what is new is that a wrong *type* now produces that 400 instead of
the 500 the old handlers raised on `{"priority": "high"}`.

No field carries a `load_default`. That is deliberate: marshmallow applies
`load_default` even under `partial=True`, so defaults declared on the shared
field set would silently reset every omitted field on a PATCH-style update.
Defaults are applied by the create schema's `post_load` instead, where they
only affect creation.
"""
from marshmallow import EXCLUDE, Schema, fields, post_load, validate

from src.models.task_model import (
    DEFAULT_PRIORITY,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    STATUS_PENDING,
    VALID_STATUSES,
)

DATE_FORMAT = "%Y-%m-%d"
_DATE_ERROR = "Formato de data inválido. Use YYYY-MM-DD"

#: The order the original handlers checked fields in, so the message promoted
#: to the top-level `error` key is the one a client saw before.
FIELD_ORDER = ("title", "status", "priority", "user_id", "category_id",
               "due_date", "tags", "description")


def _title_field(required: bool) -> fields.Field:
    """One definition of the title rules, shared by create and update.

    The three length validators are separate so each can carry the message the
    original code returned: empty, too short and too long were distinct.
    """
    return fields.Str(
        required=required,
        validate=[
            validate.Length(min=1, error="Título é obrigatório"),
            validate.Length(min=MIN_TITLE_LENGTH, error="Título muito curto"),
            validate.Length(max=MAX_TITLE_LENGTH, error="Título muito longo"),
        ],
        error_messages={
            "required": "Título é obrigatório",
            "null": "Título é obrigatório",
            "invalid": "Título inválido",
        },
    )


class _TaskFields(Schema):
    """Field rules with no defaults — see the module docstring."""

    class Meta:
        unknown = EXCLUDE

    description = fields.Str(allow_none=True,
                             error_messages={"invalid": "Descrição inválida"})
    status = fields.Str(
        validate=validate.OneOf(VALID_STATUSES, error="Status inválido"),
        error_messages={"invalid": "Status inválido", "null": "Status inválido"},
    )
    priority = fields.Int(
        validate=validate.Range(
            min=MIN_PRIORITY, max=MAX_PRIORITY,
            error="Prioridade deve ser entre 1 e 5",
        ),
        error_messages={"invalid": "Prioridade inválida",
                        "null": "Prioridade inválida"},
    )
    user_id = fields.Int(allow_none=True,
                         error_messages={"invalid": "Usuário inválido"})
    category_id = fields.Int(allow_none=True,
                             error_messages={"invalid": "Categoria inválida"})
    due_date = fields.DateTime(
        format=DATE_FORMAT, allow_none=True,
        error_messages={"invalid": _DATE_ERROR, "format": _DATE_ERROR},
    )
    # Accepts a list or a pre-joined string, as the original did; the model's
    # `tag_list` setter normalizes both.
    tags = fields.Raw(allow_none=True)


class TaskCreateSchema(_TaskFields):
    title = _title_field(required=True)

    @post_load
    def apply_creation_defaults(self, data, **_kwargs):
        data.setdefault("description", "")
        data.setdefault("status", STATUS_PENDING)
        data.setdefault("priority", DEFAULT_PRIORITY)
        data.setdefault("user_id", None)
        data.setdefault("category_id", None)
        data.setdefault("due_date", None)
        data.setdefault("tags", None)
        return data


class TaskUpdateSchema(_TaskFields):
    """Same rules, nothing required — derived, not rewritten.

    This is what prevents the create/update drift the audit found on the
    category endpoints, where update validated nothing create required.
    """

    title = _title_field(required=False)

    def __init__(self, **kwargs):
        kwargs.setdefault("partial", True)
        super().__init__(**kwargs)
