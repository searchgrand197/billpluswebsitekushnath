import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render


def _billvice_dist_dir():
    return (Path(settings.BASE_DIR) / "frontend" / "dist").resolve()


def serve_billvice(request, path=""):
    """Serve Billvice React SPA from frontend/dist (assets + index.html fallback)."""
    build_dir = _billvice_dist_dir()
    index_file = build_dir / "index.html"
    if not index_file.is_file():
        raise Http404(
            "Billvice frontend build missing. Run: cd frontend && npm install && npm run build"
        )
    if path:
        file_path = (build_dir / path).resolve()
        if build_dir not in file_path.parents and file_path != build_dir:
            raise Http404()
        if file_path.is_file():
            content_type, _ = mimetypes.guess_type(str(file_path))
            return FileResponse(
                open(file_path, "rb"),
                content_type=content_type or "application/octet-stream",
            )
    return render(request, "index.html")
