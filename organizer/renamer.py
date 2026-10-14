from pathlib import Path
from datetime import datetime
from .history import save_operation
from .logger import log

def batch_rename(folder, pattern):
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("Please select a valid folder.")
    if not pattern.strip():
        raise ValueError("Rename pattern cannot be empty.")

    files = sorted([p for p in folder.iterdir() if p.is_file()], key=lambda p: p.name.lower())
    if not files:
        return 0

    planned = []
    reserved = {p.name for p in files}
    for index, path in enumerate(files, 1):
        values = {
            "number": f"{index:03d}",
            "name": path.stem,
            "date": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d"),
            "extension": path.suffix.lstrip("."),
        }
        try:
            new_stem = pattern.format(**values)
        except KeyError as exc:
            raise ValueError(f"Unknown placeholder: {exc.args[0]}") from exc

        # Keep original extension unless pattern explicitly ends with it.
        new_name = new_stem
        if not Path(new_name).suffix:
            new_name += path.suffix

        if any(ch in new_name for ch in '<>:"/\\|?*'):
            raise ValueError(f"Pattern creates an invalid filename: {new_name}")
        planned.append((path, new_name))

    target_names = [name.lower() for _, name in planned]
    if len(target_names) != len(set(target_names)):
        raise ValueError("Pattern creates duplicate filenames.")

    # Two-stage rename prevents collisions such as a.txt -> b.txt while b.txt exists.
    temp_pairs = []
    for index, (old, new_name) in enumerate(planned):
        temp = old.with_name(f".__fileorganizer_tmp_{index}_{old.name}")
        old.rename(temp)
        temp_pairs.append((old, temp, new_name))

    actions = []
    try:
        for old, temp, new_name in temp_pairs:
            target = folder / new_name
            if target.exists():
                raise FileExistsError(f"Target already exists: {target.name}")
            temp.rename(target)
            actions.append({"from": str(old), "to": str(target)})
            log(f"RENAME {old} -> {target}")
    except Exception:
        # Best-effort rollback of temporary names and completed renames.
        for action in reversed(actions):
            cur, orig = Path(action["to"]), Path(action["from"])
            if cur.exists() and not orig.exists():
                cur.rename(orig)
        for old, temp, _ in temp_pairs:
            if temp.exists() and not old.exists():
                temp.rename(old)
        raise

    if actions:
        save_operation("rename", actions)
    return len(actions)
