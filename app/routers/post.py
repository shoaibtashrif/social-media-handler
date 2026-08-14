"""
routers/post.py
POST /api/post-now  — manually trigger an immediate Quran post
GET  /api/status    — last N posts from tracker CSV
GET  /api/verse-pool — show configured verse pool
"""
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["posting"])


class PostNowResponse(BaseModel):
    message: str
    details: dict | None = None


@router.post("/post-now", response_model=PostNowResponse)
async def post_now(background_tasks: BackgroundTasks):
    """
    Trigger an immediate Quran video post to Instagram + Facebook.
    Runs in the background; returns immediately with a confirmation.
    """
    background_tasks.add_task(_run_job)
    return PostNowResponse(message="Quran post job started in background. Check /api/status for results.")


@router.post("/post-now/sync", response_model=PostNowResponse)
def post_now_sync():
    """
    Trigger a Quran post synchronously (blocks until done).
    Useful for testing.
    """
    from app.jobs.quran_video_job import run_quran_post_job
    try:
        result = run_quran_post_job()
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


def _run_job():
    from app.jobs.quran_video_job import run_quran_post_job
    try:
        run_quran_post_job()
    except Exception as exc:
        logger.error("Background post job failed: %s", exc)
