"""
routers/post.py
POST /api/post-now  — manually trigger an immediate Quran post
GET  /api/status    — last N posts from tracker CSV
GET  /api/verse-pool — show configured verse pool
"""
import logging
import shutil
import os
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from app.services import posting_service
from app.jobs import post_tracker
from app import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["posting"])


class PostNowRequest(BaseModel):
    media_type: str = "any"
    ai_prompt: str | None = None
    qari_index: int | None = None
    audio_mode: str = "heavy"  # "heavy", "minor", or "original"

class PostNowResponse(BaseModel):
    message: str
    details: dict | None = None


@router.post("/post-now", response_model=PostNowResponse)
async def post_now(request: PostNowRequest, background_tasks: BackgroundTasks):
    """
    Trigger an immediate Quran video post to Instagram + Facebook.
    Runs in the background; returns immediately with a confirmation.
    """
    background_tasks.add_task(_run_job, request.media_type, request.ai_prompt, request.qari_index, request.audio_mode)
    return PostNowResponse(message="Quran post job started in background.")


@router.post("/post-now/sync", response_model=PostNowResponse)
def post_now_sync(request: PostNowRequest):
    """
    Trigger a Quran post synchronously (blocks until done).
    Useful for testing.
    """
    from app.jobs.quran_video_job import run_quran_post_job
    try:
        result = run_quran_post_job(
            qari_index=request.qari_index,
            media_type=request.media_type,
            ai_prompt=request.ai_prompt,
            audio_mode=request.audio_mode,
        )
        return PostNowResponse(message="Post complete", details=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
def get_status(n: int = Query(default=20, ge=1, le=200)):
    """Return the last N posts from the tracker CSV."""
    from app.jobs.post_tracker import get_recent_posts
    posts = get_recent_posts(n)
    return {"count": len(posts), "posts": posts}


@router.get("/verse-pool")
def get_verse_pool():
    """Return the configured verse pool."""
    from app import config
    return {
        "verse_pool": [
            {"surah": s, "start": st, "end": en}
            for s, st, en in config.VERSE_POOL
        ],
        "qaris": config.QARIS,
        "post_times": config.POST_TIMES,
        "timezone": config.TIMEZONE,
    }


def _run_job(media_type: str = "any", ai_prompt: str | None = None, qari_index: int | None = None, audio_mode: str = "heavy"):
    from app.jobs.quran_video_job import run_quran_post_job
    try:
        run_quran_post_job(
            qari_index=qari_index,
            media_type=media_type,
            ai_prompt=ai_prompt,
            audio_mode=audio_mode,
        )
    except Exception as exc:
        logger.error("Background post job failed: %s", exc)

@router.post("/manual-upload")
async def manual_upload(
    file: UploadFile = File(...),
    caption: str = Form(...)
):
    try:
        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        file_path = config.TEMP_DIR / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        public_url = f"{config.TUNNEL_URL}/media/{file.filename}"
        
        result = posting_service.post_to_all(
            video_url=public_url,
            video_path=str(file_path),
            caption=caption,
        )
        
        ig_id = result["ig_post_id"]
        fb_id = result["fb_post_id"]
        yt_id = result.get("yt_post_id")
        status = "success" if (ig_id or fb_id or yt_id) else "failed"

        post_tracker.log_post(
            reciter="Custom Upload",
            surah=0,
            surah_name="Custom",
            start_ayah=0,
            end_ayah=0,
            duration_s=0.0,
            video_file=file.filename,
            video_url=public_url,
            ig_post_id=ig_id,
            fb_post_id=fb_id,
            yt_post_id=yt_id,
            status=status,
            notes="Manual video upload via UI",
        )
        
        # Cleanup
        if file_path.exists():
            os.remove(file_path)
            
        return {"status": "success", "message": "Uploaded and posted successfully"}
    except Exception as exc:
        logger.error("Manual upload failed: %s", exc)
        return {"status": "error", "message": str(exc)}
