"""EXIF utility functions for image validation, metadata extraction, and thumbnails."""

from __future__ import annotations

from typing import Any

from PIL import Image, ExifTags, UnidentifiedImageError

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}

EXIF_FIELD_NAMES = {
    "DateTime",
    "Make",
    "Model",
    "FocalLength",
    "ISOSpeedRatings",
    "GPSInfo",
}

# Map EXIF tag IDs to names once at module load
_TAG_ID_TO_NAME: dict[int, str] = {v: k for k, v in ExifTags.TAGS.items()}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_image(filepath: str) -> None:
    """Raise ValueError if filepath is not a JPEG, PNG, or WEBP image.

    Detection is based on actual file content via Pillow, not file extension.
    """
    try:
        with Image.open(filepath) as img:
            fmt = img.format
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Cannot open image file '{filepath}': {exc}") from exc

    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported image format '{fmt}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )


def extract_exif(filepath: str) -> dict[str, Any]:
    """Return a dict with exactly the 6 required EXIF keys.

    Values are plain Python primitives (JSON-serializable).
    Missing or unconvertible fields return None.
    """
    result: dict[str, Any] = {key: None for key in EXIF_FIELD_NAMES}

    with Image.open(filepath) as img:
        raw = img._getexif()  # noqa: SLF001 — no public API equivalent

    if raw is None:
        return result

    name_to_value: dict[str, Any] = {}
    for tag_id, value in raw.items():
        name = ExifTags.TAGS.get(tag_id)
        if name in EXIF_FIELD_NAMES:
            name_to_value[name] = value

    for field in EXIF_FIELD_NAMES:
        if field not in name_to_value:
            continue
        value = name_to_value[field]
        result[field] = _to_serializable(field, value)

    return result


def generate_thumbnail(src_path: str, dest_path: str, width: int = 300) -> str:
    """Save a JPEG thumbnail of src_path at dest_path with the given width.

    Aspect ratio is preserved. Returns dest_path.
    """
    with Image.open(src_path) as img:
        orig_width, orig_height = img.size
        height = round(orig_height * width / orig_width)
        thumb = img.resize((width, height), Image.LANCZOS)
        thumb.save(dest_path, "JPEG")
    return dest_path


def merge_exif(extracted: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict merging extracted with overrides.

    For each key: override value wins when non-None, otherwise falls back to
    the extracted value. Neither input dict is mutated.
    """
    return {
        key: (overrides[key] if overrides.get(key) is not None else extracted.get(key))
        for key in set(extracted) | set(overrides)
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_serializable(field: str, value: Any) -> Any:
    """Convert an EXIF value to a JSON-serializable Python type."""
    if field == "GPSInfo":
        return _convert_gps(value)
    if field == "FocalLength":
        return _rational_to_float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, tuple):
        return [_rational_to_float(v) for v in value]
    # IFDRational or similar — try float/int conversion
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    return str(value)


def _rational_to_float(value: Any) -> float | None:
    """Convert IFDRational, tuple-rational, or numeric to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    # Handle (numerator, denominator) tuples
    if isinstance(value, tuple) and len(value) == 2:
        num, den = value
        if den == 0:
            return None
        return float(num) / float(den)
    return None


def _convert_gps(gps_info: Any) -> dict[str, Any] | None:
    """Convert GPSInfo IFDDictionary to a plain serializable dict."""
    if gps_info is None:
        return None
    try:
        result: dict[str, Any] = {}
        for tag_id, value in gps_info.items():
            tag_name = ExifTags.GPSTAGS.get(tag_id, str(tag_id))
            result[tag_name] = _gps_value_to_serializable(value)
        return result
    except (AttributeError, TypeError):
        return None


def _gps_value_to_serializable(value: Any) -> Any:
    """Convert a single GPS tag value to a JSON-serializable type."""
    if isinstance(value, tuple):
        return [_rational_to_float(v) for v in value]
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)
