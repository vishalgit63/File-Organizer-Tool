# Smart File Organizer

Responsive Tkinter desktop dashboard for file organization and cleanup.

## Features
- Automatic file categorization
- Dashboard scan: total files, storage used, duplicate copies, large files (>100 MB)
- Category count/progress visualization
- Preview before organizing
- Duplicate detection with SHA-256
- Duplicate Manager and **Delete Duplicate Copies** (keeps the first copy in each group)
- Batch renaming with `{number}`, `{name}`, `{date}`, `{extension}`
- Operation logs
- Undo last categorization or rename operation

## Run
```bash
python main.py
```
Python 3.10+ recommended. No third-party package is required.

## Safety
Duplicate deletion is permanent and is intentionally **not** part of Undo. The app asks for confirmation and keeps one file from every identical-content group. Test the project on a temporary folder before using important data.

## Category colors

The dashboard uses a different color for each file category:

- Documents — Blue
- Images — Purple
- Videos — Red
- Audio — Green
- Archives — Orange
- Code — Cyan
- Others — Slate Gray

The category progress bars update after every scan.

## Professional UI refresh

The interface has been visually refined without changing the application's features or workflow. It retains the same dashboard statistics, horizontal action toolbar, colored file categories, activity/results panel, duplicate management, batch rename, logs, and undo behavior.
