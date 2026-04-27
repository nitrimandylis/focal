"""Pure-function model layer — all functions take db as first arg, return dicts.

No Flask imports. No mutation of input arguments.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    """Convert a sqlite3.Row to a plain dict, parsing JSON fields."""
    if row is None:
        return None
    d = dict(row)
    for field in ("exif_extracted_json", "exif_overrides_json", "filter_json"):
        if field in d and isinstance(d[field], str):
            d[field] = json.loads(d[field])
        elif field in d and d[field] is None:
            d[field] = None
    return d


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------


def insert_photo(
    db: sqlite3.Connection,
    filename: str,
    thumb_filename: str,
    exif_extracted: dict,
) -> dict:
    """Insert a new photo row and return it as a dict."""
    upload_date = _now_utc()
    exif_json = json.dumps(exif_extracted)
    cursor = db.execute(
        """
        INSERT INTO photos (filename, thumb_filename, upload_date, exif_extracted_json)
        VALUES (?, ?, ?, ?)
        """,
        (filename, thumb_filename, upload_date, exif_json),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM photos WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_dict(row)


def get_photo(db: sqlite3.Connection, photo_id: int) -> dict | None:
    """Return a photo dict by id, or None if not found."""
    row = db.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
    return _row_to_dict(row)


def list_photos(
    db: sqlite3.Connection,
    tag_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    camera_model: str | None = None,
) -> list[dict]:
    """Return all photos matching the given filters."""
    query = "SELECT DISTINCT p.* FROM photos p"
    conditions: list[str] = []
    params: list[Any] = []

    if tag_id is not None:
        query += " JOIN photo_tags pt ON pt.photo_id = p.id"
        conditions.append("pt.tag_id = ?")
        params.append(tag_id)

    if date_from is not None:
        conditions.append("p.upload_date >= ?")
        params.append(date_from)

    if date_to is not None:
        conditions.append("p.upload_date <= ?")
        params.append(date_to)

    if camera_model is not None:
        conditions.append("json_extract(p.exif_extracted_json, '$.Model') = ?")
        params.append(camera_model)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    rows = db.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def delete_photo(db: sqlite3.Connection, photo_id: int) -> None:
    """Delete a photo and its associated photo_tags rows (cascade)."""
    db.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
    db.commit()


def update_notes(db: sqlite3.Connection, photo_id: int, notes: str) -> dict:
    """Update the notes field for a photo and return the updated photo dict."""
    if get_photo(db, photo_id) is None:
        raise ValueError(f"Photo {photo_id} not found")
    db.execute("UPDATE photos SET notes = ? WHERE id = ?", (notes, photo_id))
    db.commit()
    return get_photo(db, photo_id)


def update_exif_overrides(
    db: sqlite3.Connection, photo_id: int, fields_dict: dict
) -> dict:
    """Merge fields_dict into existing exif_overrides_json and return updated photo."""
    if get_photo(db, photo_id) is None:
        raise ValueError(f"Photo {photo_id} not found")
    row = db.execute(
        "SELECT exif_overrides_json FROM photos WHERE id = ?", (photo_id,)
    ).fetchone()
    existing_raw = row["exif_overrides_json"] if row else None
    existing: dict = json.loads(existing_raw) if existing_raw else {}
    merged = {**existing, **fields_dict}
    db.execute(
        "UPDATE photos SET exif_overrides_json = ? WHERE id = ?",
        (json.dumps(merged), photo_id),
    )
    db.commit()
    return get_photo(db, photo_id)


def reset_exif_overrides(db: sqlite3.Connection, photo_id: int) -> dict:
    """Set exif_overrides_json to NULL and return the updated photo dict."""
    if get_photo(db, photo_id) is None:
        raise ValueError(f"Photo {photo_id} not found")
    db.execute(
        "UPDATE photos SET exif_overrides_json = NULL WHERE id = ?", (photo_id,)
    )
    db.commit()
    return get_photo(db, photo_id)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def insert_tag(db: sqlite3.Connection, name: str, color: str) -> dict:
    """Insert a new tag and return it as a dict."""
    cursor = db.execute(
        "INSERT INTO tags (name, color) VALUES (?, ?)", (name, color)
    )
    db.commit()
    row = db.execute("SELECT * FROM tags WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_dict(row)


def list_tags(db: sqlite3.Connection) -> list[dict]:
    """Return all tags as a list of dicts."""
    rows = db.execute("SELECT * FROM tags ORDER BY name").fetchall()
    return [_row_to_dict(r) for r in rows]


def delete_tag(db: sqlite3.Connection, tag_id: int) -> None:
    """Delete a tag by id."""
    db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    db.commit()


# ---------------------------------------------------------------------------
# Photo-Tags
# ---------------------------------------------------------------------------


def add_tag_to_photo(db: sqlite3.Connection, photo_id: int, tag_id: int) -> None:
    """Associate a tag with a photo (idempotent via INSERT OR IGNORE)."""
    db.execute(
        "INSERT OR IGNORE INTO photo_tags (photo_id, tag_id) VALUES (?, ?)",
        (photo_id, tag_id),
    )
    db.commit()


def remove_tag_from_photo(db: sqlite3.Connection, photo_id: int, tag_id: int) -> None:
    """Remove the association between a photo and a tag."""
    db.execute(
        "DELETE FROM photo_tags WHERE photo_id = ? AND tag_id = ?",
        (photo_id, tag_id),
    )
    db.commit()


def get_tags_for_photo(db: sqlite3.Connection, photo_id: int) -> list[dict]:
    """Return all tags associated with a photo."""
    rows = db.execute(
        """
        SELECT t.* FROM tags t
        JOIN photo_tags pt ON pt.tag_id = t.id
        WHERE pt.photo_id = ?
        ORDER BY t.name
        """,
        (photo_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Galleries
# ---------------------------------------------------------------------------


def create_gallery(db: sqlite3.Connection, filter_json: dict) -> dict:
    """Create a new gallery with a unique UUID token and return it as a dict."""
    token = str(uuid.uuid4())
    created_at = _now_utc()
    filter_str = json.dumps(filter_json)
    cursor = db.execute(
        "INSERT INTO galleries (token, filter_json, created_at) VALUES (?, ?, ?)",
        (token, filter_str, created_at),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM galleries WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_dict(row)


def get_gallery(db: sqlite3.Connection, token: str) -> dict | None:
    """Return a gallery dict by token, or None if not found."""
    row = db.execute(
        "SELECT * FROM galleries WHERE token = ?", (token,)
    ).fetchone()
    return _row_to_dict(row)
