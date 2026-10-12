"""Rate limits, scoped to the endpoints that need them (T-16/API-04).

A global limit would throttle read traffic for no benefit. These two cover what
the audit identified: unthrottled credential attempts against `/login`, and
unthrottled destructive calls.
"""
from src.config.settings import settings
from src.extensions import limiter

#: Credential attempts. Combined with real password hashing this is what makes
#: brute force impractical rather than merely slow.
login_limit = limiter.limit(settings.LOGIN_RATE_LIMIT)

#: Destructive operations, as a backstop against a runaway client.
destructive_limit = limiter.limit(settings.DESTRUCTIVE_RATE_LIMIT)
