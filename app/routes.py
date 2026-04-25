"""Flask Blueprint containing all application routes.

All model and exif_utils calls go through module-level imports so they
can be cleanly patched in tests.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

import config
from app import exif_utils, models
from app.db import get_db

bp = Blueprint("main", __name__)

# Allowed file extensions (lower-case, without leading dot)
_ALLOWED = config.ALLOWED_EXTENSIONS

# Filter keys for gallery generation
_FILTER_KEYS = {"tag_id", "date_from", "date_to", "camera_model"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _allowed_extension(filename: str) -> bool:
    """Return True when *filename* has an extension in ALLOWED_EXTENSIONS."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in _ALLOWED


def _error(message: str, status: int):
    """Return a JSON error response."""
    return jsonify({"error": message}), status


def _not_found():
    """Return a standard 404 JSON response."""
    return jsonify({"error": "not found"}), 404


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------


@bp.route("/")
def index():
    """Gallery grid — list all photos and tags."""
    db = get_db()
    photos = models.list_photos(db)
    tags = models.list_tags(db)
    return render_template("index.html", photos=photos, tags=tags)


@bp.route("/upload", methods=["GET"])
def upload_page():
    """Render the upload page."""
    return render_template("upload.html")


@bp.route("/upload", methods=["POST"])
def upload():
    """Accept a file upload, validate, save, extract EXIF, generate thumbnail."""
    if "file" not in request.files:
        return _error("No file in request", 400)

    file = request.files["file"]

    if file.filename == "" or file.filename is None:
        return _error("No file selected", 400)

    if not _allowed_extension(file.filename):
        return _error(
            f"File extension not allowed. Allowed: {', '.join(sorted(_ALLOWED))}",
            400,
        )

    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}.{ext}"
    thumb_filename = f"thumb_{unique_id}.{ext}"

    original_path = os.path.join(config.UPLOAD_FOLDER, filename)
    thumb_path = os.path.join(config.THUMB_FOLDER, thumb_filename)

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.THUMB_FOLDER, exist_ok=True)

    file.save(original_path)

    try:
        exif_utils.validate_image(original_path)
    except ValueError as exc:
        os.remove(original_path)
        return _error(str(exc), 400)

    exif_data = exif_utils.extract_exif(original_path)
    exif_utils.generate_thumbnail(original_path, thumb_path, width=config.THUMB_WIDTH)

    db = get_db()
    models.insert_photo(db, filename, thumb_filename, exif_data)

    return redirect(url_for("main.index"))


@bp.route("/photo/<int:photo_id>")
def photo_detail(photo_id: int):
    """Photo detail — full image, EXIF panel, tags, notes."""
    db = get_db()
    photo = models.get_photo(db, photo_id)
    if photo is None:
        return _not_found()

    tags = models.get_tags_for_photo(db, photo_id)
    extracted = photo.get("exif_extracted_json") or {}
    overrides = photo.get("exif_overrides_json") or {}
    merged_exif = exif_utils.merge_exif(extracted, overrides)

    return render_template("photo.html", photo=photo, tags=tags, exif=merged_exif)


@bp.route("/gallery/<token>")
def gallery(token: str):
    """Read-only shareable gallery view."""
    db = get_db()
    gallery_record = models.get_gallery(db, token)
    if gallery_record is None:
        return _not_found()

    stored_filter: dict[str, Any] = gallery_record.get("filter_json") or {}
    # Coerce tag_id to int if present
    if "tag_id" in stored_filter and stored_filter["tag_id"] is not None:
        stored_filter = {**stored_filter, "tag_id": int(stored_filter["tag_id"])}

    photos = models.list_photos(db, **stored_filter)
    return render_template("gallery.html", gallery=gallery_record, photos=photos)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@bp.route("/photo/<int:photo_id>/tag", methods=["POST"])
def photo_tag(photo_id: int):
    """Add or remove a tag from a photo. Body: {tag_id, action: 'add'|'remove'}."""
    db = get_db()
    photo = models.get_photo(db, photo_id)
    if photo is None:
        return _not_found()

    body = request.get_json(silent=True) or {}
    tag_id = body.get("tag_id")
    action = body.get("action")

    if tag_id is None or action not in ("add", "remove"):
        return _error("Invalid request body: need tag_id and action (add|remove)", 400)

    try:
        if action == "add":
            models.add_tag_to_photo(db, photo_id, int(tag_id))
        else:
            models.remove_tag_from_photo(db, photo_id, int(tag_id))
    except ValueError as exc:
        return _error(str(exc), 400)

    return jsonify({"ok": True})


@bp.route("/photo/<int:photo_id>/notes", methods=["POST"])
def update_notes(photo_id: int):
    """Update notes field for a photo."""
    db = get_db()
    photo = models.get_photo(db, photo_id)
    if photo is None:
        return _not_found()

    body = request.get_json(silent=True) or {}
    notes = body.get("notes", "")

    try:
        models.update_notes(db, photo_id, notes)
    except ValueError as exc:
        return _error(str(exc), 400)

    return jsonify({"ok": True})


@bp.route("/photo/<int:photo_id>/exif", methods=["POST"])
def update_exif(photo_id: int):
    """Merge JSON body fields into exif_overrides_json for a photo."""
    db = get_db()
    photo = models.get_photo(db, photo_id)
    if photo is None:
        return _not_found()

    fields = request.get_json(silent=True) or {}
    try:
        models.update_exif_overrides(db, photo_id, fields)
    except ValueError as exc:
        return _error(str(exc), 400)

    return jsonify({"ok": True})


@bp.route("/photo/<int:photo_id>/exif", methods=["DELETE"])
def reset_exif(photo_id: int):
    """Reset exif_overrides_json to NULL for a photo."""
    db = get_db()
    photo = models.get_photo(db, photo_id)
    if photo is None:
        return _not_found()

    try:
        models.reset_exif_overrides(db, photo_id)
    except ValueError as exc:
        return _error(str(exc), 400)

    return jsonify({"ok": True})


@bp.route("/photo/<int:photo_id>", methods=["DELETE"])
def delete_photo(photo_id: int):
    """Delete a photo and remove its files from disk."""
    db = get_db()
    photo = models.get_photo(db, photo_id)
    if photo is None:
        return _not_found()

    original_path = os.path.join(config.UPLOAD_FOLDER, photo["filename"])
    thumb_path = os.path.join(config.THUMB_FOLDER, photo["thumb_filename"])

    models.delete_photo(db, photo_id)

    if os.path.exists(original_path):
        os.remove(original_path)
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    return jsonify({"ok": True})


@bp.route("/gallery/generate")
def gallery_generate():
    """Generate a shareable gallery token from query-param filters."""
    raw = {k: v for k, v in request.args.items() if k in _FILTER_KEYS}

    # Coerce tag_id to int when provided
    if "tag_id" in raw:
        try:
            raw = {**raw, "tag_id": int(raw["tag_id"])}
        except (ValueError, TypeError):
            return _error("tag_id must be an integer", 400)

    db = get_db()
    gallery_record = models.create_gallery(db, raw)
    token = gallery_record["token"]
    url = url_for("main.gallery", token=token, _external=True)
    return jsonify({"token": token, "url": url})


@bp.route("/api/photos")
def api_photos():
    """Return a JSON array of photos, optionally filtered by query params."""
    tag_id_raw = request.args.get("tag_id")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    camera_model = request.args.get("camera_model")

    tag_id: int | None = None
    if tag_id_raw is not None:
        try:
            tag_id = int(tag_id_raw)
        except ValueError:
            return _error("tag_id must be an integer", 400)

    db = get_db()
    photos = models.list_photos(
        db,
        tag_id=tag_id,
        date_from=date_from,
        date_to=date_to,
        camera_model=camera_model,
    )
    return jsonify(photos)
