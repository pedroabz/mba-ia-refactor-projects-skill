"""Populate the database with the example dataset.

    python seed.py

Kept at the project root because that is how the README documents it. The
logic lives in src/seed.py; this only builds the app and calls it.
"""
from src.app import create_app
from src.seed import seed_data

if __name__ == "__main__":
    seed_data(create_app())
