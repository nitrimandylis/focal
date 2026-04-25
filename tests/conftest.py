"""Shared pytest fixtures for route tests."""

import pytest
from flask import Flask


@pytest.fixture()
def app():
    """Create a minimal Flask app with the main blueprint registered."""
    flask_app = Flask(
        __name__,
        template_folder="../app/templates",
    )
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    from app.routes import bp
    flask_app.register_blueprint(bp)

    return flask_app


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()
