from pathlib import Path
import hashlib
from collections import defaultdict
from .logger import log

def file_hash(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()

def find_duplicates(folder):
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("Please select a valid folder.")

    # Group by size first so we only hash possible duplicates.
    sizes = defaultdict(list)
    for path in folder.rglob("*"):
        if path.is_file():
            try:
                sizes[path.stat().st_size].append(path)
            except OSError:
                pass

    hashes = defaultdict(list)
    for same_size_files in sizes.values():
        if len(same_size_files) < 2:
            continue
        for path in same_size_files:
            try:
                hashes[file_hash(path)].append(path)
            except (OSError, PermissionError):
                pass

    groups = [paths for paths in hashes.values() if len(paths) > 1]
    log(f"DUPLICATE_SCAN {folder} | groups={len(groups)}")
    return groups

def delete_duplicates(groups):
    """Keep the first file in every group and delete the remaining copies."""
    deleted = []
    failed = []
    for group in groups:
        for path in group[1:]:
            try:
                path.unlink()
                deleted.append(path)
                log(f"DELETE_DUPLICATE {path}")
            except OSError as exc:
                failed.append((path, str(exc)))
    return deleted, failed
