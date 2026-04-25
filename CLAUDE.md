# Photo Manager — IB CS IA

## Project Overview

A standalone desktop photo management application. The user is a photographer who manages a Sony Cyber-shot photo library. The app replaces manual folder-based organization with a structured, searchable, and tagged system.

## Stack

- **Backend:** Python + Flask
- **Frontend:** HTML + CSS (Jinja2 templates)
- **Desktop wrapper:** pywebview (renders Flask app in a native OS window, no browser)
- **Packaging:** PyInstaller (single binary for macOS/Windows)
- **Database:** SQLite via Python's built-in `sqlite3` module
- **Image processing:** Pillow (thumbnails + EXIF extraction)

## Folder Structure

```
photo_manager/
  app/
    static/
      photos/
        originals/
        thumbs/
    templates/
    models.py
    routes.py
    exif_utils.py
    __init__.py
  db.sqlite
  run.py
  main.py          # pywebview entry point
```

## Database Schema

```sql
photos:     id, filename, thumb_filename, upload_date, exif_json, notes
tags:       id, name, color
photo_tags: photo_id, tag_id
galleries:  id, token, filter_json, created_at
```

## Pages

| Route | Purpose |
|---|---|
| `/` | Gallery grid, filter by tag/date/camera |
| `/upload` | Drag-and-drop multi-file upload |
| `/photo/<id>` | Detail view, EXIF panel, tag editor, notes |
| `/gallery/<token>` | Public read-only shareable gallery |

## API Routes

| Method | Route | Action |
|---|---|---|
| POST | `/upload` | Save file, extract EXIF, insert DB, generate thumbnail |
| POST | `/photo/<id>/tag` | Add or remove tag |
| DELETE | `/photo/<id>` | Delete photo and all associated data |
| GET | `/gallery/generate` | Create UUID token, return shareable link |
| GET | `/api/photos` | JSON list for JS filtering |

## EXIF Fields to Store

`DateTime`, `Make`, `Model`, `FocalLength`, `ISOSpeedRatings`, `GPSInfo`

## Success Criteria

1. Allow the user to upload one or multiple photos from the local file system
2. Automatically extract and display EXIF metadata (date, camera model, focal length, ISO) from each uploaded photo
3. Generate and store a thumbnail for each photo
4. Allow the user to add, edit, and remove tags for each photo
5. Filter the photo library by tag, date range, or camera model
6. Display all photos in a grid layout with thumbnails
7. Allow the user to view a full-size photo alongside its metadata on a detail screen
8. Validate uploaded files to ensure only supported image formats are accepted
9. Allow the user to delete a photo and its associated data from the library
10. Generate a shareable collection by exporting a selected set of photos and their metadata to a folder
11. Show a loading indicator during upload and thumbnail generation
12. Highlight the active filter or sort option in the UI
13. Allow the user to add freeform notes to a photo from the detail page
14. Show EXIF data in a collapsible panel on the detail page
15. Support drag-and-drop file upload on the upload page
16. Display photo count and total library size in the gallery header

## Key Constraints

- Single-user app, no authentication needed
- All data stays local
- Supported formats: JPEG, PNG, WEBP
- Thumbnail size: 300px width
- Out of scope: map view, bulk edit, search by notes
