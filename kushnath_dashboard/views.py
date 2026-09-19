import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import redirect


def _resolve_build_path(relative_path=""):
    build_dir = Path(settings.FRONTEND_BUILD_DIR).resolve()
    file_path = (build_dir / relative_path).resolve()

    if file_path != build_dir and build_dir not in file_path.parents:
        raise Http404()

    return file_path


def serve_frontend(request, path=""):
    """Serve legacy Live React assets from build/; never steal /billvice/."""
    # Safety: /billvice must never hit this catch-all (would redirect to storefront home)
    if path == "billvice" or path.startswith("billvice/"):
        from kushnath.billvice_views import serve_billvice

        sub = "" if path == "billvice" else path[len("billvice/") :]
        return serve_billvice(request, path=sub)

    if path:
        file_path = _resolve_build_path(path)
        if file_path.is_file():
            content_type, _ = mimetypes.guess_type(str(file_path))
            response = FileResponse(
                open(file_path, "rb"),
                content_type=content_type or "application/octet-stream",
            )
            if file_path.suffix == ".html":
                response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            elif file_path.suffix in {".js", ".css"}:
                response["Cache-Control"] = "public, max-age=31536000, immutable"
            return response

    # Old Live SPA client routes → Django storefront home
    return redirect("/")
