"""Configuracao da aplicacao, lida do ambiente.

Nenhum segredo e literal aqui: SECRET_KEY e obrigatoria e a ausencia dela
interrompe o boot, em vez de cair para um valor conhecido.
"""
import os


class ConfigError(RuntimeError):
    """Configuracao ausente ou invalida — levantada no boot, nunca em runtime."""


def _required(env, name):
    value = env.get(name)
    if not value:
        raise ConfigError(
            f"Variavel de ambiente obrigatoria ausente: {name}. "
            "Veja .env.example para a lista completa."
        )
    return value


def _flag(env, name, default=False):
    return env.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _integer(env, name, default):
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} deve ser um numero inteiro, recebido: {raw!r}") from exc


def _list(env, name, default):
    raw = env.get(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """Snapshot imutavel da configuracao do processo."""

    __slots__ = (
        "SECRET_KEY", "DEBUG", "HOST", "PORT", "DATABASE_PATH", "SEED_ON_BOOT",
        "LOG_LEVEL", "CORS_ORIGINS", "MAX_CONTENT_LENGTH", "TOKEN_TTL_SECONDS",
        "RATE_LIMIT_ENABLED", "LOGIN_RATE_LIMIT", "ADMIN_RATE_LIMIT",
        "DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE", "API_VERSION",
    )

    def __init__(self, env=None):
        env = os.environ if env is None else env

        self.SECRET_KEY = _required(env, "SECRET_KEY")
        self.DEBUG = _flag(env, "DEBUG", False)
        self.HOST = env.get("HOST", "127.0.0.1")
        # 5001 e nao 5000: no macOS o AirPlay Receiver ocupa a 5000 em `*:5000`
        # (IPv4 e IPv6), entao `localhost:5000` responde 403 pelo AirTunes em vez
        # de chegar na aplicacao. Sobrescreva com PORT se precisar de outra.
        self.PORT = _integer(env, "PORT", 5001)

        self.DATABASE_PATH = env.get("DATABASE_PATH", "loja.db")
        self.SEED_ON_BOOT = _flag(env, "SEED_ON_BOOT", True)

        self.LOG_LEVEL = env.get("LOG_LEVEL", "INFO").upper()
        self.CORS_ORIGINS = _list(env, "CORS_ORIGINS", ("http://localhost:3000",))
        self.MAX_CONTENT_LENGTH = _integer(env, "MAX_CONTENT_LENGTH", 100 * 1024)

        self.TOKEN_TTL_SECONDS = _integer(env, "TOKEN_TTL_SECONDS", 3600)
        self.RATE_LIMIT_ENABLED = _flag(env, "RATE_LIMIT_ENABLED", True)
        self.LOGIN_RATE_LIMIT = _integer(env, "LOGIN_RATE_LIMIT", 20)
        self.ADMIN_RATE_LIMIT = _integer(env, "ADMIN_RATE_LIMIT", 60)

        self.DEFAULT_PAGE_SIZE = _integer(env, "DEFAULT_PAGE_SIZE", 50)
        self.MAX_PAGE_SIZE = _integer(env, "MAX_PAGE_SIZE", 200)

        self.API_VERSION = "1.0.0"

        if self.DEBUG and self.HOST not in ("127.0.0.1", "localhost"):
            raise ConfigError(
                "DEBUG=true com HOST publico expoe o console interativo do Werkzeug "
                "(execucao remota de codigo). Use HOST=127.0.0.1 ou DEBUG=false."
            )


def load_settings(env=None):
    """Carrega a configuracao. Chamada pelo composition root, nao por import lateral."""
    return Settings(env)
