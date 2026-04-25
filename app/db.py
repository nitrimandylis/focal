import sqlite3
import threading

import config

_local = threading.local()

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    thumb_filename TEXT NOT NULL,
    upload_date TEXT NOT NULL,
    exif_extracted_json TEXT,
    exif_overrides_json TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#888888'
);

CREATE TABLE IF NOT EXISTS photo_tags (
    photo_id INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (photo_id, tag_id)
);

CREATE TABLE IF NOT EXISTS galleries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    filter_json TEXT,
    created_at TEXT NOT NULL
);
"""

EXPECTED_TABLES = {"photos", "tags", "photo_tags", "galleries"}


def get_db():
    """Return a thread-local sqlite3 connection to DB_PATH."""
    if not hasattr(_local, "connection") or _local.connection is None:
        _local.connection = sqlite3.connect(config.DB_PATH)
        _local.connection.execute("PRAGMA foreign_keys = ON")
        _local.connection.row_factory = sqlite3.Row
    return _local.connection


def init_db(db):
    """Run schema DDL. Idempotent — safe to call multiple times."""
    db.executescript(SCHEMA_DDL)
    db.commit()


def close_db(db):
    """Close the given database connection."""
    if db is not None:
        db.close()
    if hasattr(_local, "connection") and _local.connection is db:
        _local.connection = None
