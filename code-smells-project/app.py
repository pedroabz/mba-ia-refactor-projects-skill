"""Ponto de entrada do processo.

Carrega a configuracao, pede a aplicacao ao composition root (`src/app.py`) e
sobe o servidor. Nada mais: nenhuma rota, nenhuma consulta, nenhum segredo.
"""
import sys

from src.app import create_app
from src.config.settings import ConfigError, load_settings


def build():
    try:
        settings = load_settings()
    except ConfigError as erro:
        print(f"Erro de configuração: {erro}", file=sys.stderr)
        raise SystemExit(1) from erro
    return settings, create_app(settings)


# Exposto em nivel de modulo para servidores WSGI: `gunicorn "app:app"`.
settings, app = build()


if __name__ == "__main__":
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
