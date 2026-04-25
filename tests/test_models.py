"""Tests for app/models.py — one test per function, TDD style."""

import json
import sqlite3

import pytest

from app.db import init_db
from app import models


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_insert_photo(db):
    exif = {"Model": "DSC-RX100", "ISO": 200}
    result = models.insert_photo(db, "img.jpg", "img_thumb.jpg", exif)

    assert result["id"] == 1
    assert result["filename"] == "img.jpg"
    assert result["thumb_filename"] == "img_thumb.jpg"
    assert result["exif_extracted_json"] == exif
    assert result["upload_date"] is not None
    assert result["notes"] is None
    assert result["exif_overrides_json"] is None


@pytest.mark.unit
def test_get_photo_exists(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    result = models.get_photo(db, 1)
    assert result is not None
    assert result["id"] == 1
    assert result["filename"] == "a.jpg"


@pytest.mark.unit
def test_get_photo_missing(db):
    result = models.get_photo(db, 999)
    assert result is None


@pytest.mark.unit
def test_list_photos_all(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    models.insert_photo(db, "b.jpg", "b_t.jpg", {})
    results = models.list_photos(db)
    assert len(results) == 2


@pytest.mark.unit
def test_list_photos_filter_by_tag(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    models.insert_photo(db, "b.jpg", "b_t.jpg", {})
    tag = models.insert_tag(db, "nature", "#00ff00")
    models.add_tag_to_photo(db, 1, tag["id"])

    results = models.list_photos(db, tag_id=tag["id"])
    assert len(results) == 1
    assert results[0]["id"] == 1


@pytest.mark.unit
def test_list_photos_filter_by_date(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    results = models.list_photos(db, date_from="2020-01-01", date_to="2099-12-31")
    assert len(results) == 1


@pytest.mark.unit
def test_list_photos_filter_by_camera_model(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {"Model": "DSC-RX100"})
    models.insert_photo(db, "b.jpg", "b_t.jpg", {"Model": "iPhone"})
    results = models.list_photos(db, camera_model="DSC-RX100")
    assert len(results) == 1
    assert results[0]["filename"] == "a.jpg"


@pytest.mark.unit
def test_delete_photo(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    models.delete_photo(db, 1)
    assert models.get_photo(db, 1) is None


@pytest.mark.unit
def test_delete_photo_cascades_photo_tags(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    tag = models.insert_tag(db, "x", "#111111")
    models.add_tag_to_photo(db, 1, tag["id"])
    models.delete_photo(db, 1)
    rows = db.execute("SELECT * FROM photo_tags WHERE photo_id = 1").fetchall()
    assert len(rows) == 0


@pytest.mark.unit
def test_update_notes(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    result = models.update_notes(db, 1, "Great shot!")
    assert result["notes"] == "Great shot!"
    assert result["id"] == 1


@pytest.mark.unit
def test_update_exif_overrides_merge(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {"Model": "DSC-RX100"})
    models.update_exif_overrides(db, 1, {"ISO": 400})
    result = models.update_exif_overrides(db, 1, {"FocalLength": "24mm"})
    assert result["exif_overrides_json"]["ISO"] == 400
    assert result["exif_overrides_json"]["FocalLength"] == "24mm"


@pytest.mark.unit
def test_reset_exif_overrides(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    models.update_exif_overrides(db, 1, {"ISO": 400})
    result = models.reset_exif_overrides(db, 1)
    assert result["exif_overrides_json"] is None


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_insert_tag(db):
    result = models.insert_tag(db, "travel", "#ff0000")
    assert result["id"] == 1
    assert result["name"] == "travel"
    assert result["color"] == "#ff0000"


@pytest.mark.unit
def test_list_tags(db):
    models.insert_tag(db, "a", "#111111")
    models.insert_tag(db, "b", "#222222")
    results = models.list_tags(db)
    assert len(results) == 2
    assert {r["name"] for r in results} == {"a", "b"}


@pytest.mark.unit
def test_delete_tag(db):
    models.insert_tag(db, "x", "#aaaaaa")
    models.delete_tag(db, 1)
    assert models.list_tags(db) == []


# ---------------------------------------------------------------------------
# Photo-Tags
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_add_tag_to_photo(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    models.insert_tag(db, "x", "#aaaaaa")
    models.add_tag_to_photo(db, 1, 1)
    tags = models.get_tags_for_photo(db, 1)
    assert len(tags) == 1
    assert tags[0]["name"] == "x"


@pytest.mark.unit
def test_remove_tag_from_photo(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    models.insert_tag(db, "x", "#aaaaaa")
    models.add_tag_to_photo(db, 1, 1)
    models.remove_tag_from_photo(db, 1, 1)
    assert models.get_tags_for_photo(db, 1) == []


@pytest.mark.unit
def test_get_tags_for_photo_empty(db):
    models.insert_photo(db, "a.jpg", "a_t.jpg", {})
    assert models.get_tags_for_photo(db, 1) == []


# ---------------------------------------------------------------------------
# Galleries
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_gallery(db):
    result = models.create_gallery(db, {"tag_id": 1})
    assert "token" in result
    assert len(result["token"]) == 36  # UUID format
    assert result["filter_json"] == {"tag_id": 1}
    assert result["created_at"] is not None


@pytest.mark.unit
def test_get_gallery_exists(db):
    created = models.create_gallery(db, {})
    result = models.get_gallery(db, created["token"])
    assert result is not None
    assert result["token"] == created["token"]


@pytest.mark.unit
def test_get_gallery_missing(db):
    result = models.get_gallery(db, "nonexistent-token")
    assert result is None
