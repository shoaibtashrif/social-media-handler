"""
routers/media.py — GET /media/{filename}
Serves generated video files so Instagram can fetch them via the public tunnel URL.
Files are served from config.VIDEO_DIR.
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app import config

router = APIRouter(tags=["media"])


@router.get("/media/{filename}")
def serve_media(filename: str):
    """
    Serve a generated video file by filename.
    Instagram needs this public URL to fetch the video before publishing.
    """
    # Basic security: no path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = config.VIDEO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    media_type = "video/mp4" if filename.endswith(".mp4") else "application/octet-stream"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )
