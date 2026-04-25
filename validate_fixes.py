#!/usr/bin/env python3
"""
Validation script for the two database layer fixes.
Tests that:
1. Foreign key pragma is enabled in get_db()
2. Config paths use pathlib and are anchored to project root
"""

import sys
import sqlite3
from pathlib import Path

# Test 1: Verify foreign key pragma is enabled
print("Test 1: Checking foreign key pragma in app/db.py...")
with open("app/db.py", "r") as f:
    db_content = f.read()
    if 'PRAGMA foreign_keys = ON' in db_content:
        print("✓ Foreign key pragma found in get_db()")
    else:
        print("✗ Foreign key pragma NOT found in get_db()")
        sys.exit(1)

# Test 2: Verify config uses pathlib
print("\nTest 2: Checking pathlib-anchored paths in config.py...")
with open("config.py", "r") as f:
    config_content = f.read()
    checks = [
        ("from pathlib import Path", "pathlib import"),
        ("BASE_DIR = Path(__file__).parent", "BASE_DIR definition"),
        ("str(BASE_DIR / \"db.sqlite\")", "DB_PATH with BASE_DIR"),
        ("str(BASE_DIR / \"app\" / \"static\" / \"photos\" / \"originals\")", "UPLOAD_FOLDER with BASE_DIR"),
        ("str(BASE_DIR / \"app\" / \"static\" / \"photos\" / \"thumbs\")", "THUMB_FOLDER with BASE_DIR"),
    ]

    for check, desc in checks:
        if check in config_content:
            print(f"✓ {desc}")
        else:
            print(f"✗ {desc} NOT found")
            sys.exit(1)

# Test 3: Verify constants are unchanged
print("\nTest 3: Checking other constants are unchanged...")
import config
expected = {
    "ALLOWED_EXTENSIONS": {"jpg", "jpeg", "png", "webp"},
    "THUMB_WIDTH": 300,
    "MAX_CONTENT_LENGTH": 50 * 1024 * 1024,
}
for key, expected_val in expected.items():
    actual_val = getattr(config, key)
    if actual_val == expected_val:
        print(f"✓ {key} unchanged")
    else:
        print(f"✗ {key} changed! Expected {expected_val}, got {actual_val}")
        sys.exit(1)

# Test 4: Verify paths resolve correctly
print("\nTest 4: Testing path resolution...")
print(f"  DB_PATH: {config.DB_PATH}")
print(f"  UPLOAD_FOLDER: {config.UPLOAD_FOLDER}")
print(f"  THUMB_FOLDER: {config.THUMB_FOLDER}")

# Test 5: Verify get_db() returns a working connection with pragma enabled
print("\nTest 5: Testing get_db() with foreign key pragma...")
from app.db import get_db, init_db, close_db
import config as cfg
cfg.DB_PATH = ":memory:"
from app import db as db_module
db_module._local.connection = None

try:
    conn = get_db()
    cursor = conn.cursor()

    # Check if foreign keys are enabled
    cursor.execute("PRAGMA foreign_keys")
    fk_enabled = cursor.fetchone()[0]
    if fk_enabled == 1:
        print("✓ Foreign keys pragma enabled on connection")
    else:
        print("✗ Foreign keys pragma NOT enabled on connection")
        sys.exit(1)

    # Basic query test
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    if result and result[0] == 1:
        print("✓ Connection can execute queries")
    else:
        print("✗ Connection query failed")
        sys.exit(1)

    close_db(conn)
finally:
    db_module._local.connection = None

print("\n" + "="*50)
print("All validation tests passed!")
print("="*50)
