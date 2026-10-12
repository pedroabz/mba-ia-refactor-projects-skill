"""Authentication and authorization (T-05).

The application previously issued `fake-jwt-token-<id>` and never verified it
anywhere, so every destructive and bulk-read endpoint was open (SEC-05). Tokens
are now signed with the application's SECRET_KEY and carry an expiry, and the
guards below are applied at the route layer so a controller cannot be reached
unguarded.

`itsdangerous` ships with Flask, so this adds no dependency.
"""
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.config.logging_config import get_logger
from src.middlewares.error_handler import Forbidden, Unauthorized
from src.models.user_model import User

logger = get_logger(__name__)

_SALT = "task-manager-auth"
_BEARER_PREFIX = "bearer "


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_SALT)


def issue_token(user: User) -> str:
    """Sign a token identifying the user. Carries no credential material."""
    return _serializer().dumps({"uid": user.id, "role": user.role})


def _token_from_request() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith(_BEARER_PREFIX):
        return header[len(_BEARER_PREFIX):].strip()
    return None


def authenticate() -> User | None:
    """Resolve the caller from the request, verifying the signature.

    Returns None when there is no valid token — the guards decide what that
    means, so an endpoint can be public without bypassing verification.
    """
    token = _token_from_request()
    if not token:
        return None
    ttl = current_app.config["SETTINGS"].TOKEN_TTL_SECONDS
    try:
        payload = _serializer().loads(token, max_age=ttl)
    except SignatureExpired:
        logger.info("token rejected: expired")
        return None
    except BadSignature:
        logger.warning("token rejected: bad signature")
        return None

    user = User.get_by_id(payload.get("uid"))
    if user is None or not user.active:
        return None
    return user


def current_user() -> User | None:
    """The authenticated caller for this request, if any."""
    return getattr(g, "current_user", None)


def require_auth(view):
    """Any authenticated, active user may proceed."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        user = authenticate()
        if user is None:
            raise Unauthorized("Autenticação necessária")
        g.current_user = user
        return view(*args, **kwargs)

    return wrapper


def require_role(*roles: str):
    """Only the named roles may proceed. Deny by default."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = authenticate()
            if user is None:
                raise Unauthorized("Autenticação necessária")
            if user.role not in roles:
                logger.info(
                    "role check failed: user %s has %s, needs one of %s",
                    user.id, user.role, roles,
                )
                raise Forbidden("Permissão insuficiente para esta operação")
            g.current_user = user
            return view(*args, **kwargs)

        return wrapper

    return decorator


def require_self_or_privileged(param: str = "user_id"):
    """Ownership check: the caller may act on their own record, or must be
    privileged to act on someone else's.

    Role alone is not enough where a resource belongs to a specific user, which
    is why this exists alongside `require_role`.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = authenticate()
            if user is None:
                raise Unauthorized("Autenticação necessária")
            target_id = kwargs.get(param)
            if target_id != user.id and not user.is_privileged:
                raise Forbidden("Permissão insuficiente para esta operação")
            g.current_user = user
            return view(*args, **kwargs)

        return wrapper

    return decorator
