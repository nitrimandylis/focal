"""Desktop entry point — wraps Flask in a pywebview native window."""

import threading

import webview

from app import create_app


def start_flask() -> None:
    """Start Flask in a background daemon thread."""
    flask_app = create_app()
    flask_app.run(port=5000, use_reloader=False)


if __name__ == "__main__":
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()
    webview.create_window("Photo Manager", "http://localhost:5000")
    webview.start()
