"""Tests for app/exif_utils.py — written before implementation (TDD)."""

import json
import os
import tempfile

import pytest
from PIL import Image

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_JPG = os.path.join(FIXTURES_DIR, "sample.jpg")

EXIF_KEYS = {"DateTime", "Make", "Model", "FocalLength", "ISOSpeedRatings", "GPSInfo"}


# ---------------------------------------------------------------------------
# validate_image
# ---------------------------------------------------------------------------

def test_validate_image_accepts_jpg():
    from app.exif_utils import validate_image
    # Should not raise
    validate_image(SAMPLE_JPG)


def test_validate_image_rejects_non_image():
    from app.exif_utils import validate_image
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("not an image")
        tmp_path = f.name
    try:
        with pytest.raises(ValueError):
            validate_image(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_validate_image_rejects_jpg_extension_with_text_content():
    """A file named .jpg but containing text must be rejected."""
    from app.exif_utils import validate_image
    with tempfile.NamedTemporaryFile(suffix=".jpg", mode="w", delete=False) as f:
        f.write("this is not image data")
        tmp_path = f.name
    try:
        with pytest.raises(ValueError):
            validate_image(tmp_path)
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# extract_exif
# ---------------------------------------------------------------------------

def test_extract_exif_returns_all_keys():
    from app.exif_utils import extract_exif
    result = extract_exif(SAMPLE_JPG)
    assert set(result.keys()) == EXIF_KEYS


def test_extract_exif_is_json_serializable():
    from app.exif_utils import extract_exif
    result = extract_exif(SAMPLE_JPG)
    # Must not raise
    json.dumps(result)


def test_extract_exif_missing_fields_are_none():
    """Fixture JPEG has no camera EXIF, so all values should be None."""
    from app.exif_utils import extract_exif
    result = extract_exif(SAMPLE_JPG)
    for key in EXIF_KEYS:
        assert result[key] is None


# ---------------------------------------------------------------------------
# generate_thumbnail
# ---------------------------------------------------------------------------

def test_generate_thumbnail_width():
    from app.exif_utils import generate_thumbnail
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        dest = f.name
    try:
        generate_thumbnail(SAMPLE_JPG, dest, width=300)
        thumb = Image.open(dest)
        assert thumb.width == 300
    finally:
        os.unlink(dest)


def test_generate_thumbnail_preserves_aspect_ratio():
    from app.exif_utils import generate_thumbnail
    # Create a non-square source: 200x100
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        src = f.name
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        dest = f.name
    try:
        Image.new("RGB", (200, 100)).save(src, "JPEG")
        generate_thumbnail(src, dest, width=100)
        thumb = Image.open(dest)
        assert thumb.width == 100
        assert thumb.height == 50
    finally:
        os.unlink(src)
        os.unlink(dest)


def test_generate_thumbnail_returns_dest_path():
    from app.exif_utils import generate_thumbnail
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        dest = f.name
    try:
        result = generate_thumbnail(SAMPLE_JPG, dest)
        assert result == dest
    finally:
        os.unlink(dest)


# ---------------------------------------------------------------------------
# merge_exif
# ---------------------------------------------------------------------------

def test_merge_exif_override_wins():
    from app.exif_utils import merge_exif
    extracted = {"DateTime": "2024-01-01", "Make": "Sony", "Model": None,
                 "FocalLength": None, "ISOSpeedRatings": None, "GPSInfo": None}
    overrides = {"DateTime": "2025-06-15", "Make": None, "Model": None,
                 "FocalLength": None, "ISOSpeedRatings": None, "GPSInfo": None}
    result = merge_exif(extracted, overrides)
    assert result["DateTime"] == "2025-06-15"


def test_merge_exif_fallback_to_extracted():
    from app.exif_utils import merge_exif
    extracted = {"DateTime": "2024-01-01", "Make": "Sony", "Model": None,
                 "FocalLength": None, "ISOSpeedRatings": None, "GPSInfo": None}
    overrides = {"DateTime": None, "Make": None, "Model": None,
                 "FocalLength": None, "ISOSpeedRatings": None, "GPSInfo": None}
    result = merge_exif(extracted, overrides)
    assert result["Make"] == "Sony"
    assert result["DateTime"] == "2024-01-01"


def test_merge_exif_does_not_mutate_inputs():
    from app.exif_utils import merge_exif
    extracted = {"DateTime": "2024-01-01", "Make": "Sony", "Model": None,
                 "FocalLength": None, "ISOSpeedRatings": None, "GPSInfo": None}
    overrides = {"DateTime": "2025-06-15", "Make": None, "Model": "A7",
                 "FocalLength": None, "ISOSpeedRatings": None, "GPSInfo": None}
    extracted_copy = dict(extracted)
    overrides_copy = dict(overrides)
    merge_exif(extracted, overrides)
    assert extracted == extracted_copy
    assert overrides == overrides_copy
