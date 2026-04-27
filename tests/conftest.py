"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture()
def app():
    """Create a test Flask app via the application factory."""
    flask_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            # Use an in-memory SQLite DB so tests stay isolated
            "DB_PATH": ":memory:",
        }
    )
    return flask_app


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()
