"""Service metadata: index and liveness.

These two handlers were defined inline in the old entry point. A composition
root must not define routes, so they moved here with their bodies unchanged.
"""
import datetime

from flask import jsonify


def index():
    return jsonify({'message': 'Task Manager API', 'version': '1.0'}), 200


def health():
    # Liveness only. Deliberately reports no configuration: a health check that
    # echoes settings is an information-disclosure finding.
    return jsonify({'status': 'ok', 'timestamp': str(datetime.datetime.now())}), 200
