"""
Billvice frontend serving (SPA).

Source:  frontend/          (Vite + React)
Build:   cd frontend && npm install && npm run build
Output:  frontend/dist/     (see settings.BILLVICE_DIST_DIR)

URL map:
  /billvice/              -> dist/index.html
  /billvice/login         -> dist/index.html   (React Router)
  /billvice/assets/*.js   -> dist/assets/*.js  (must be real files — never HTML)
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse

# Never SPA-fallback these — returning HTML caused:
# "Expected a JavaScript module but server responded with MIME type text/html"
_STATIC_SUFFIXES = {
    ".js",
    ".mjs",
    ".css",
    ".map",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".txt",
    ".pdf",
}

_CONTENT_TYPES = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".html": "text/html; charset=utf-8",
}


def billvice_dist_dir() -> Path:
    configured = getattr(settings, "BILLVICE_DIST_DIR", None)
    if configured:
        return Path(configured).resolve()
    return (Path(settings.BASE_DIR) / "frontend" / "dist").resolve()


def _safe_file(build_dir: Path, relative: str) -> Path | None:
    if not relative:
        return None
    # Normalize URL path separators
    relative = relative.replace("\\", "/").lstrip("/")
    file_path = (build_dir / relative).resolve()
    if build_dir not in file_path.parents and file_path != build_dir:
        raise Http404("Invalid path")
    if file_path.is_file():
        return file_path
    return None


def _content_type(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in _CONTENT_TYPES:
        return _CONTENT_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(str(file_path))
    return guessed or "application/octet-stream"


def _file_response(file_path: Path, *, cache_immutable: bool = False) -> FileResponse:
    response = FileResponse(
        open(file_path, "rb"),
        content_type=_content_type(file_path),
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
        "Run: cd frontend && npm install && npm run build\n"
        "Then upload the whole frontend/dist/ folder (index.html + assets/).\n"
    )
    return HttpResponse(msg, status=503, content_type="text/plain; charset=utf-8")


def _missing_asset_response(build_dir: Path, path: str) -> HttpResponse:
    assets_dir = build_dir / "assets"
    available = sorted(p.name for p in assets_dir.glob("*")) if assets_dir.is_dir() else []
    msg = (
        f"Billvice asset not found: {path}\n\n"
        f"Looked in: {build_dir / path}\n"
        f"Available in assets/: {', '.join(available) or '(none — upload frontend/dist/assets/)'}\n\n"
        "Fix: upload the FULL frontend/dist/ from the same build "
        "(index.html and assets/ must match).\n"
        "Do not SPA-fallback JS/CSS to index.html.\n"
    )
    return HttpResponse(msg, status=404, content_type="text/plain; charset=utf-8")


def serve_billvice(request, path=""):
    """
    Serve Billvice from frontend/dist only.

    Static files (.js/.css/...) → real file or 404 (never HTML).
    Other paths → index.html for React Router.
    """
    path = (path or "").replace("\\", "/").lstrip("/")
    build_dir = billvice_dist_dir()
    index_file = build_dir / "index.html"

    if not index_file.is_file():
        return _missing_build_response(build_dir)

    if path:
        asset = _safe_file(build_dir, path)
        suffix = Path(path).suffix.lower()
        looks_static = suffix in _STATIC_SUFFIXES or path.startswith("assets/")

        if asset is not None:
            cache_immutable = "assets/" in path and suffix in {
                ".js",
                ".mjs",
                ".css",
                ".woff",
                ".woff2",
            }
            return _file_response(asset, cache_immutable=cache_immutable)

        # Critical: never return index.html for missing JS/CSS (MIME type error in browser)
        if looks_static:
            return _missing_asset_response(build_dir, path)

    response = _file_response(index_file, cache_immutable=False)
    response["X-Billvice-Index"] = str(index_file)
    return response
