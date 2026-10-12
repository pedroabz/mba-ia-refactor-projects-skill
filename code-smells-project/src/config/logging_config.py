"""Configuracao de logging — unico lugar que define formato e nivel."""
import logging
import sys

FORMAT = (
    '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
    '"msg":"%(message)s"}'
)


def configure_logging(level="INFO"):
    """Configura o logging do processo. Idempotente: chamada pelo composition root."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(FORMAT))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
    return root
