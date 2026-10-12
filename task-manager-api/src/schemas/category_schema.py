"""Category request schemas.

The update path previously validated nothing at all: `PUT /categories/<id>`
assigned name, description and colour straight from the body, so a category
name could be set to "" through update even though create rejected a missing
name — the drift QUA-01 warned about and API-03 recorded. Deriving the update
schema from the same fields removes it, and the colour format is now checked
on both paths using the rule salvaged from the dead helpers module.
"""
from marshmallow import EXCLUDE, Schema, fields, post_load, validate

from src.models.category_model import (
    COLOR_PATTERN,
    DEFAULT_COLOR,
    MAX_NAME_LENGTH,
)

FIELD_ORDER = ("name", "color", "description")


def _name_field(required: bool) -> fields.Field:
    return fields.Str(
        required=required,
        validate=validate.Length(
            min=1, max=MAX_NAME_LENGTH, error="Nome é obrigatório"
        ),
        error_messages={
            "required": "Nome é obrigatório",
            "null": "Nome é obrigatório",
            "invalid": "Nome inválido",
        },
    )


def _color_field() -> fields.Field:
    return fields.Str(
        validate=validate.Regexp(
            COLOR_PATTERN, error="Cor inválida. Use o formato #RRGGBB"
        ),
        error_messages={"invalid": "Cor inválida. Use o formato #RRGGBB"},
    )


class _Base(Schema):
    class Meta:
        unknown = EXCLUDE


class CategoryCreateSchema(_Base):
    name = _name_field(required=True)
    description = fields.Str(allow_none=True)
    color = _color_field()

    @post_load
    def apply_creation_defaults(self, data, **_kwargs):
        data.setdefault("description", "")
        data.setdefault("color", DEFAULT_COLOR)
        return data


class CategoryUpdateSchema(_Base):
    name = _name_field(required=False)
    description = fields.Str(allow_none=True)
    color = _color_field()

    def __init__(self, **kwargs):
        kwargs.setdefault("partial", True)
        super().__init__(**kwargs)
