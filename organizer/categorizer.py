from pathlib import Path
import shutil
from .config import CATEGORIES
from .history import save_operation
from .logger import log

def category_for(path):
    ext = path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"

def _unique_path(path):
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1

def organize_folder(folder):
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("Please select a valid folder.")

    actions = []
    # Only organize files directly inside selected folder to avoid repeatedly
    # reorganizing category folders.
    for item in list(folder.iterdir()):
        if not item.is_file():
            continue
        destination_dir = folder / category_for(item)
        destination_dir.mkdir(exist_ok=True)
        destination = _unique_path(destination_dir / item.name)
        shutil.move(str(item), str(destination))
        actions.append({"from": str(item), "to": str(destination)})
        log(f"MOVE {item} -> {destination}")

    if actions:
        save_operation("categorize", actions)
    return len(actions)
