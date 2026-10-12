"""User and login request schemas."""
from marshmallow import EXCLUDE, Schema, fields, post_load, validate

from src.models.user_model import (
    EMAIL_PATTERN,
    MIN_PASSWORD_LENGTH,
    ROLE_USER,
    VALID_ROLES,
)

#: The order the original handler checked fields in: presence of name, email
#: and password, then email format, then password length, then role.
FIELD_ORDER = ("name", "email", "password", "role", "active")


def _email_field(required: bool) -> fields.Field:
    return fields.Str(
        required=required,
        validate=[
            validate.Length(min=1, error="Email é obrigatório"),
            validate.Regexp(EMAIL_PATTERN, error="Email inválido"),
        ],
        error_messages={
            "required": "Email é obrigatório",
            "null": "Email é obrigatório",
            "invalid": "Email inválido",
        },
    )


def _password_field(required: bool, short_message: str) -> fields.Field:
    return fields.Str(
        required=required,
        validate=[
            validate.Length(min=1, error="Senha é obrigatória"),
            validate.Length(min=MIN_PASSWORD_LENGTH, error=short_message),
        ],
        error_messages={
            "required": "Senha é obrigatória",
            "null": "Senha é obrigatória",
            "invalid": "Senha inválida",
        },
    )


def _name_field(required: bool) -> fields.Field:
    return fields.Str(
        required=required,
        validate=validate.Length(min=1, max=100, error="Nome é obrigatório"),
        error_messages={
            "required": "Nome é obrigatório",
            "null": "Nome é obrigatório",
            "invalid": "Nome inválido",
        },
    )


def _role_field(required: bool) -> fields.Field:
    return fields.Str(
        required=required,
        validate=validate.OneOf(VALID_ROLES, error="Role inválido"),
        error_messages={"invalid": "Role inválido", "null": "Role inválido"},
    )


class _Base(Schema):
    class Meta:
        unknown = EXCLUDE


class UserCreateSchema(_Base):
    name = _name_field(required=True)
    email = _email_field(required=True)
    # Never silently defaulted: an account created with a known password is a
    # security finding, so a missing password is an error.
    password = _password_field(
        required=True,
        short_message=f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres",
    )
    role = _role_field(required=False)

    @post_load
    def apply_creation_defaults(self, data, **_kwargs):
        data.setdefault("role", ROLE_USER)
        return data


class UserUpdateSchema(_Base):
    """Same field rules as creation, all optional."""

    name = _name_field(required=False)
    email = _email_field(required=False)
    password = _password_field(required=False, short_message="Senha muito curta")
    role = _role_field(required=False)
    # Typed, where the old handler assigned whatever JSON value arrived into a
    # boolean column.
    active = fields.Bool(error_messages={"invalid": "Valor inválido para active"})

    def __init__(self, **kwargs):
        kwargs.setdefault("partial", True)
        super().__init__(**kwargs)


class LoginSchema(_Base):
    email = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Email e senha são obrigatórios"),
        error_messages={
            "required": "Email e senha são obrigatórios",
            "null": "Email e senha são obrigatórios",
            "invalid": "Email e senha são obrigatórios",
        },
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Email e senha são obrigatórios"),
        error_messages={
            "required": "Email e senha são obrigatórios",
            "null": "Email e senha são obrigatórios",
            "invalid": "Email e senha são obrigatórios",
        },
    )


LOGIN_FIELD_ORDER = ("email", "password")
