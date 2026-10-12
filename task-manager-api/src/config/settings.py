"""Environment-driven configuration (T-01).

Every value that varies by environment lives here and nowhere else. Secrets are
required with no fallback: a missing SECRET_KEY stops the boot rather than
silently reinstating the committed default this replaced.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is two levels up from src/config/settings.py. Resolving it from
# __file__ rather than the working directory means `python wsgi.py` and
# `flask --app src.app db upgrade` both find the same .env.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# python-dotenv was a declared dependency that nothing imported (LAY-06). This
# is the import that makes it do its job. Real environment variables win over
# the file, so a deployment can override without editing it.
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _csv(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _database_url(raw: str) -> str:
    """Anchor a relative SQLite path to the project root.

    Flask derives a relative sqlite path from its own instance path, which
    moved when the app module became `src.app`. Resolving it here keeps the
    database file in one predictable place no matter who builds the app or from
    which working directory.
    """
    prefix = "sqlite:///"
    if raw.startswith(prefix):
        path = raw[len(prefix):]
        if path and not path.startswith("/") and not path.startswith(":"):
            return f"{prefix}{PROJECT_ROOT / path}"
    return raw


class Settings:
    """Application settings, read once at import of the composition root."""

    # --- secrets: required, never defaulted -------------------------------
    # A default secret in production is the original vulnerability again, so a
    # missing value is a boot failure. Local development supplies it via .env.
    SECRET_KEY: str = os.environ.get("SECRET_KEY") or ""

    # --- persistence ------------------------------------------------------
    DATABASE_URL: str = _database_url(os.getenv("DATABASE_URL", "sqlite:///tasks.db"))
    SQLALCHEMY_ECHO: bool = _flag("SQLALCHEMY_ECHO")

    # --- runtime ----------------------------------------------------------
    # Defaults are development-safe: debug off, loopback only. The previous
    # entry point shipped debug=True on 0.0.0.0, which exposed the Werkzeug
    # console to every interface (SEC-06).
    DEBUG: bool = _flag("DEBUG")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "5000"))

    # --- HTTP boundary ----------------------------------------------------
    CORS_ORIGINS: list[str] = _csv("CORS_ORIGINS", "http://localhost:3000")
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH_BYTES", str(256 * 1024)))
    TOKEN_TTL_SECONDS: int = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))

    # --- rate limits ------------------------------------------------------
    # Scoped to the endpoints that need them. Login is the one that matters:
    # brute force against it was entirely unthrottled.
    LOGIN_RATE_LIMIT: str = os.getenv("LOGIN_RATE_LIMIT", "10 per minute")
    DESTRUCTIVE_RATE_LIMIT: str = os.getenv("DESTRUCTIVE_RATE_LIMIT", "60 per minute")

    # --- pagination -------------------------------------------------------
    # Deployment policy rather than a domain rule, so it belongs here.
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "200"))

    # --- observability ----------------------------------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    def validate(self) -> None:
        """Fail fast on anything that must not fall back to a default."""
        if not self.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY is not set. Copy .env.example to .env and set it, or "
                "export it in the environment. There is deliberately no default: "
                "a known signing key is what this refactor removed."
            )
        if self.DEBUG and self.HOST not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError(
                f"Refusing to start: DEBUG=true with HOST={self.HOST}. The Werkzeug "
                "debugger executes arbitrary code, so it must never listen on a "
                "non-loopback interface."
            )


settings = Settings()
