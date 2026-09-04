"""Remove studio black/white backgrounds from official product PNGs (p01–p21)."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from django.conf import settings
from PIL import Image


def _is_background(r: int, g: int, b: int, a: int, *, dark_threshold: int = 55) -> bool:
    if a < 30:
        return True
    if r < dark_threshold and g < dark_threshold and b < dark_threshold:
        return True
    if r > 230 and g > 230 and b > 230:
        return True
    return False


def remove_image_background(src: Path, dest: Path | None = None) -> int:
    """Flood-fill edge-connected studio backgrounds to transparent. Returns pixels cleared."""
    dest = dest or src
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = [[False] * w for _ in range(h)]
    queue: deque[tuple[int, int]] = deque()

    def seed(x: int, y: int) -> None:
        if not bg[y][x] and _is_background(*px[x, y]):
            bg[y][x] = True
            queue.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)
    for y in range(h):
        for x in range(w):
            if px[x, y][3] < 10:
                seed(x, y)

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and not bg[ny][nx] and _is_background(*px[nx, ny]):
                bg[ny][nx] = True
                queue.append((nx, ny))

    removed = 0
    for y in range(h):
        for x in range(w):
            if bg[y][x]:
                px[x, y] = (0, 0, 0, 0)
                removed += 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, optimize=True)
    return removed


def remove_official_backgrounds() -> dict:
    folder = Path(settings.MEDIA_ROOT) / "products" / "official"
    backup = folder / "_backup_before_transparent"
    backup.mkdir(exist_ok=True)

    results = []
    for src in sorted(folder.glob("p*.png")):
        if src.name.endswith("_test.png") or src.parent.name == "_backup_before_transparent":
            continue
        backup_path = backup / src.name
        if not backup_path.exists():
            backup_path.write_bytes(src.read_bytes())

        removed = remove_image_background(src)
        results.append({"file": src.name, "removed_pixels": removed})

    return {"processed": len(results), "files": results}
