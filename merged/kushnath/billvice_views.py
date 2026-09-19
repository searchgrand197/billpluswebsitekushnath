"""
Billvice frontend serving (SPA).

Source:  frontend/          (Vite + React)
Build:   cd frontend && npm install && npm run build
Output:  frontend/dist/     (see settings.BILLVICE_DIST_DIR)

URL map (all handled here — do not point nginx at build/ for these):
  /billvice/              -> dist/index.html
  /billvice/login         -> dist/index.html   (React Router client route)
  /billvice/assets/*.js   -> dist/assets/*.js  (hashed Vite files)

Vite base and React basename must both be "/billvice/".
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def billvice_dist_dir() -> Path:
    configured = getattr(settings, "BILLVICE_DIST_DIR", None)
    if configured:
        return Path(configured).resolve()
    return (Path(settings.BASE_DIR) / "frontend" / "dist").resolve()


def _safe_file(build_dir: Path, relative: str) -> Path | None:
    """Return a file under build_dir, or None if missing / outside dist."""
    if not relative:
        return None
    file_path = (build_dir / relative).resolve()
    if build_dir not in file_path.parents and file_path != build_dir:
        raise Http404("Invalid path")
    if file_path.is_file():
        return file_path
    return None


def _file_response(file_path: Path, *, cache_immutable: bool = False) -> FileResponse:
    content_type, _ = mimetypes.guess_type(str(file_path))
    response = FileResponse(
        open(file_path, "rb"),
        content_type=content_type or "application/octet-stream",
    )
    if cache_immutable:
        response["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


def _missing_build_response(build_dir: Path) -> HttpResponse:
    msg = (
        "Billvice frontend build not found.\n\n"
        f"Expected: {build_dir / 'index.html'}\n\n"
        "On the server (or before deploy), run:\n"
        "  cd frontend\n"
        "  npm install\n"
        "  npm run build\n\n"
        "Then ensure frontend/dist/ is uploaded next to manage.py.\n"
        "Vite must use base: '/billvice/' (see frontend/vite.config.js).\n"
    )
    return HttpResponse(msg, status=503, content_type="text/plain; charset=utf-8")


def serve_billvice(request, path=""):
    """
    Serve Billvice only from frontend/dist (never from templates/ or build/).

    Always returns dist/index.html for unknown paths so React Router can handle
    /billvice/login, /billvice/pos, etc.
    """
    build_dir = billvice_dist_dir()
    index_file = build_dir / "index.html"

    if not index_file.is_file():
        return _missing_build_response(build_dir)

    # Real static file under dist (assets, favicon, etc.)
    if path:
        asset = _safe_file(build_dir, path)
        if asset is not None:
            immutable = asset.suffix in {".js", ".css", ".woff", ".woff2", ".png", ".svg", ".jpg", ".jpeg", ".webp"}
            # Hashed Vite assets are immutable; favicons can be short-cached via same header OK
            return _file_response(asset, cache_immutable=immutable and "assets" in path.replace("\\", "/"))

    # SPA fallback — always the Billvice index from dist, never Django templates
    return _file_response(index_file, cache_immutable=False)
