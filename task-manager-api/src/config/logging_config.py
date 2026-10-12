"""Logging configuration (T-23).

Replaces the seven `print()` calls that were the application's only
observability. Configured once by the composition root; level comes from config
so verbosity is an environment decision rather than a code edit.
"""
import logging
import sys

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        stream=sys.stdout,
        format=_FORMAT,
        force=True,
    )
    # The SQL echo is controlled by SQLALCHEMY_ECHO, not by the app log level.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
