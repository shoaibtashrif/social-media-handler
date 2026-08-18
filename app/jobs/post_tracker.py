import logging
import random
from app.database import SessionLocal
from app.models import PostLog
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)

def log_post(
    reciter: str,
    surah: int,
    surah_name: str,
    start_ayah: int,
    end_ayah: int,
    duration_s: float,
    video_file: str,
    video_url: str,
    ig_post_id: str | None,
    fb_post_id: str | None,
    yt_post_id: str | None = None,
    status: str = "success",
    notes: str = "",
) -> None:
    db = SessionLocal()
    try:
        post = PostLog(
            reciter=reciter,
            surah_name=f"{surah_name} ({surah})",
            verses=f"{start_ayah}-{end_ayah}",
            duration_s=duration_s,
            video_file=video_file,
            ig_post_id=ig_post_id,
            fb_post_id=fb_post_id,
            yt_post_id=yt_post_id,
            status=status,
            notes=notes
        )
        db.add(post)
        db.commit()
        logger.info(f"Database tracker updated for video: {video_file}")
    finally:
        db.close()

def get_next_qari_index(total_qaris: int) -> int:
    mode = get_setting("qari_mode", "random")
    if mode == "fixed":
        idx = int(get_setting("fixed_qari_index", 0))
        # Ensure it's in bounds
        return idx % total_qaris
    
    # Random mode
    return random.randint(0, total_qaris - 1)
