import json
from pathlib import Path
from .logger import log

BASE = Path(__file__).resolve().parent.parent
HISTORY_FILE = BASE / "data" / "history.json"
HISTORY_FILE.parent.mkdir(exist_ok=True)

def _load():
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

def _save(history):
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")

def save_operation(operation_type, actions):
    history = _load()
    history.append({"type": operation_type, "actions": actions})
    _save(history)

def undo_last():
    history = _load()
    if not history:
        return False, "Nothing to undo."

    operation = history[-1]
    undone = 0
    errors = []

    # Reverse order is important when restoring a batch.
    for action in reversed(operation["actions"]):
        current = Path(action["to"])
        original = Path(action["from"])
        try:
            if current.exists():
                original.parent.mkdir(parents=True, exist_ok=True)
                if original.exists():
                    errors.append(f"Cannot restore {original.name}: destination already exists.")
                    continue
                current.rename(original)
                log(f"UNDO {current} -> {original}")
                undone += 1
        except OSError as exc:
            errors.append(str(exc))

    if errors:
        return False, f"Undid {undone} item(s). Some items could not be restored:\n" + "\n".join(errors)

    history.pop()
    _save(history)
    return True, f"Undo complete. Restored {undone} item(s)."
