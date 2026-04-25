"""Tests for app/routes.py — all model and exif_utils calls are mocked."""

import io
import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PHOTO = {
    "id": 1,
    "filename": "abc.jpg",
    "thumb_filename": "thumb_abc.jpg",
    "upload_date": "2024-01-01T00:00:00+00:00",
    "exif_extracted_json": {"DateTime": None, "Make": "Sony", "Model": "DSC-RX100M7",
                             "FocalLength": None, "ISOSpeedRatings": None, "GPSInfo": None},
    "exif_overrides_json": None,
    "notes": None,
}

GALLERY = {
    "id": 1,
    "token": "test-token-uuid",
    "filter_json": {"camera_model": "DSC-RX100M7"},
    "created_at": "2024-01-01T00:00:00+00:00",
}

TAG = {"id": 1, "name": "nature", "color": "#00ff00"}


def _mock_db():
    return MagicMock()


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_index_returns_200(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.list_photos", return_value=[PHOTO]), \
         patch("app.routes.models.list_tags", return_value=[TAG]):
        resp = client.get("/")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /upload
# ---------------------------------------------------------------------------

def test_get_upload_returns_200(client):
    resp = client.get("/upload")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

def _fake_image_bytes() -> bytes:
    """Minimal bytes — file.save() is mocked so content doesn't matter."""
    return b"FAKEJPEGDATA"


def test_post_upload_valid_file_redirects(client, tmp_path):
    data = {
        "file": (io.BytesIO(_fake_image_bytes()), "photo.jpg"),
    }
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.config.UPLOAD_FOLDER", str(tmp_path / "originals")), \
         patch("app.routes.config.THUMB_FOLDER", str(tmp_path / "thumbs")), \
         patch("app.routes.exif_utils.validate_image"), \
         patch("app.routes.exif_utils.extract_exif", return_value={}), \
         patch("app.routes.exif_utils.generate_thumbnail", return_value="thumb.jpg"), \
         patch("app.routes.models.insert_photo", return_value=PHOTO):
        # Create dirs so os.makedirs doesn't fail if routes try to ensure they exist
        (tmp_path / "originals").mkdir(parents=True)
        (tmp_path / "thumbs").mkdir(parents=True)
        resp = client.post(
            "/upload",
            data=data,
            content_type="multipart/form-data",
        )
    assert resp.status_code == 302


def test_post_upload_no_file_returns_400(client):
    resp = client.post("/upload", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400
    body = resp.get_json()
    assert body is not None
    assert "error" in body


def test_post_upload_invalid_extension_returns_400(client):
    data = {
        "file": (io.BytesIO(b"data"), "malware.exe"),
    }
    resp = client.post(
        "/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert "error" in body


# ---------------------------------------------------------------------------
# GET /photo/<id>
# ---------------------------------------------------------------------------

def test_get_photo_existing_returns_200(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_photo", return_value=PHOTO), \
         patch("app.routes.models.get_tags_for_photo", return_value=[TAG]), \
         patch("app.routes.exif_utils.merge_exif", return_value={}):
        resp = client.get("/photo/1")
    assert resp.status_code == 200


def test_get_photo_missing_returns_404(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_photo", return_value=None):
        resp = client.get("/photo/999")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["error"] == "not found"


# ---------------------------------------------------------------------------
# DELETE /photo/<id>
# ---------------------------------------------------------------------------

def test_delete_photo_returns_200(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_photo", return_value=PHOTO), \
         patch("app.routes.models.delete_photo"), \
         patch("app.routes.os.path.exists", return_value=False):
        resp = client.delete("/photo/1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True


# ---------------------------------------------------------------------------
# POST /photo/<id>/tag
# ---------------------------------------------------------------------------

def test_post_photo_tag_add_returns_200(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_photo", return_value=PHOTO), \
         patch("app.routes.models.add_tag_to_photo"):
        resp = client.post(
            "/photo/1/tag",
            data=json.dumps({"tag_id": 1, "action": "add"}),
            content_type="application/json",
        )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True


def test_post_photo_tag_remove_returns_200(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_photo", return_value=PHOTO), \
         patch("app.routes.models.remove_tag_from_photo"):
        resp = client.post(
            "/photo/1/tag",
            data=json.dumps({"tag_id": 1, "action": "remove"}),
            content_type="application/json",
        )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


# ---------------------------------------------------------------------------
# POST /photo/<id>/exif
# ---------------------------------------------------------------------------

def test_post_photo_exif_returns_200(client):
    updated = {**PHOTO, "exif_overrides_json": {"Model": "DSC-RX100"}}
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_photo", return_value=PHOTO), \
         patch("app.routes.models.update_exif_overrides", return_value=updated):
        resp = client.post(
            "/photo/1/exif",
            data=json.dumps({"Model": "DSC-RX100"}),
            content_type="application/json",
        )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


# ---------------------------------------------------------------------------
# DELETE /photo/<id>/exif
# ---------------------------------------------------------------------------

def test_delete_photo_exif_returns_200(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_photo", return_value=PHOTO), \
         patch("app.routes.models.reset_exif_overrides", return_value=PHOTO):
        resp = client.delete("/photo/1/exif")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


# ---------------------------------------------------------------------------
# GET /gallery/generate
# ---------------------------------------------------------------------------

def test_gallery_generate_returns_token(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.create_gallery", return_value=GALLERY):
        resp = client.get("/gallery/generate?camera_model=DSC-RX100M7")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "token" in body
    assert "url" in body


# ---------------------------------------------------------------------------
# GET /gallery/<token>
# ---------------------------------------------------------------------------

def test_get_gallery_returns_200(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_gallery", return_value=GALLERY), \
         patch("app.routes.models.list_photos", return_value=[PHOTO]):
        resp = client.get("/gallery/test-token-uuid")
    assert resp.status_code == 200


def test_get_gallery_missing_returns_404(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.get_gallery", return_value=None):
        resp = client.get("/gallery/no-such-token")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not found"


# ---------------------------------------------------------------------------
# GET /api/photos
# ---------------------------------------------------------------------------

def test_api_photos_returns_json_array(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.list_photos", return_value=[PHOTO]):
        resp = client.get("/api/photos")
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body, list)
    assert len(body) == 1


def test_api_photos_with_filters(client):
    with patch("app.routes.get_db", return_value=_mock_db()), \
         patch("app.routes.models.list_photos", return_value=[]) as mock_lp:
        resp = client.get(
            "/api/photos?tag_id=2&date_from=2024-01-01&date_to=2024-12-31&camera_model=DSC"
        )
    assert resp.status_code == 200
    mock_lp.assert_called_once()
    call_kwargs = mock_lp.call_args
    # tag_id should be coerced to int
    assert call_kwargs[1]["tag_id"] == 2 or call_kwargs[0][1] == 2
