"""Development entry point.

    python wsgi.py

Creates the application through the factory and serves it. Host, port and debug
come from configuration; the defaults are loopback and debug-off, where the old
entry point hardcoded `debug=True, host='0.0.0.0'`.

In a deployed context a WSGI server imports `app` from this module directly
(`gunicorn wsgi:app`) and never calls `app.run`.
"""
from src.app import create_app
from src.config.settings import settings

app = create_app(settings)

if __name__ == "__main__":
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
