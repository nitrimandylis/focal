"""Application factory for the Photo Manager Flask app."""

from __future__ import annotations

import os

from flask import Flask


def create_app(config: dict | None = None) -> Flask:
    """Create and configure a Flask application instance.

    Args:
        config: Optional dict of config overrides (used in tests).

    Returns:
        Configured Flask app with blueprint registered and DB initialised.
    """
    app = Flask(__name__)

    # Load defaults from config module
    app.config.from_object("config")

    # Allow callers (e.g. tests) to override individual values
    if config:
        app.config.update(config)

    # Ensure upload/thumbnail directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["THUMB_FOLDER"], exist_ok=True)

    # Initialise database schema
    from app.db import close_db, get_db, init_db  # noqa: PLC0415

    with app.app_context():
        db = get_db()
        init_db(db)

    # Tear down thread-local DB connection at the end of each request context
    @app.teardown_appcontext
    def teardown_db(exception: BaseException | None) -> None:  # noqa: ANN001
        from app import db as db_module  # noqa: PLC0415

        if (
            hasattr(db_module._local, "connection")
            and db_module._local.connection is not None
        ):
            close_db(db_module._local.connection)

    # Register main blueprint
    from app.routes import bp  # noqa: PLC0415

    app.register_blueprint(bp)

    return app
