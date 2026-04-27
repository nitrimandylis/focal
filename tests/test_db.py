import sqlite3

import pytest

from app.db import close_db, init_db


@pytest.fixture
def mem_db():
    """Provide an in-memory SQLite connection for each test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    close_db(conn)


def _get_table_names(db):
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return {row[0] for row in cursor.fetchall()}


def test_init_db_idempotent(mem_db):
    """Calling init_db twice must not raise any error."""
    init_db(mem_db)
    init_db(mem_db)  # second call — must be a no-op, not an error


def test_all_tables_exist_after_init(mem_db):
    """All four expected tables must be present after init_db."""
    init_db(mem_db)
    tables = _get_table_names(mem_db)
    assert "photos" in tables
    assert "tags" in tables
    assert "photo_tags" in tables
    assert "galleries" in tables


def test_get_db_returns_working_cursor():
    """get_db must return a connection whose cursor can execute queries."""
    import config

    original_path = config.DB_PATH
    config.DB_PATH = ":memory:"

    # Reset any cached thread-local connection so the test uses the new path
    from app import db as db_module

    db_module._local.connection = None

    try:
        conn = db_module.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == 1
    finally:
        close_db(conn)
        db_module._local.connection = None
        config.DB_PATH = original_path
