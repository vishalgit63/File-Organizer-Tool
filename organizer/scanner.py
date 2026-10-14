from pathlib import Path
from collections import Counter
from .categorizer import category_for

LARGE_FILE_BYTES = 100 * 1024 * 1024

def human_size(size):
    value = float(size)
    for unit in ('B','KB','MB','GB','TB'):
        if value < 1024 or unit == 'TB':
            return f'{value:.1f} {unit}' if unit != 'B' else f'{int(value)} B'
        value /= 1024

def scan_folder(folder):
    folder = Path(folder)
    files = [p for p in folder.rglob('*') if p.is_file()]
    total_size = 0
    categories = Counter()
    large = []
    for p in files:
        try:
            size = p.stat().st_size
        except OSError:
            continue
        total_size += size
        categories[category_for(p)] += 1
        if size >= LARGE_FILE_BYTES:
            large.append((p, size))
    return {
        'total_files': len(files), 'total_size': total_size,
        'storage': human_size(total_size), 'categories': categories,
        'large_files': sorted(large, key=lambda x: x[1], reverse=True)
    }
