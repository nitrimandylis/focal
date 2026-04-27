from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = str(BASE_DIR / "db.sqlite")
UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "photos" / "originals")
THUMB_FOLDER = str(BASE_DIR / "app" / "static" / "photos" / "thumbs")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
THUMB_WIDTH = 300
MAX_CONTENT_LENGTH = 50 * 1024 * 1024
