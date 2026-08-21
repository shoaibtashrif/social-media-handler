"""
scheduler_service.py
Schedules 3-4 daily Quran video posts using APScheduler.
Post times are read from .env POST_TIMES (HH:MM, comma-separated, 24h PKT).
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app import config
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _job_wrapper(qari: str = "random", media_type: str = "web_video", prompt: str = "", audio_mode: str = "heavy"):
    """Wrapper so import happens at call time (avoids circular imports)."""
    from app.services.settings_service import get_setting
    if not get_setting("auto_upload", True):
        logger.info("Auto upload is disabled in settings. Skipping scheduled job.")
        return

    from app.jobs.quran_video_job import run_quran_post_job
    try:
        qari_index = None
        if qari != "random" and qari.isdigit():
            qari_index = int(qari)
        run_quran_post_job(
            qari_index=qari_index,
            media_type=media_type,
            prompt=prompt,
            audio_mode=audio_mode
        )
    except Exception as exc:
        logger.error("Scheduled job failed: %s", exc)


def _token_refresh_wrapper():
    """Daily token refresh and log truncation — runs at midnight."""
    from app.services.token_service import refresh_all_tokens
    import os
    try:
        if os.path.exists("main.log"):
            with open("main.log", "w") as f:
                f.truncate(0)
            logger.info("Midnight log wipe complete.")
            
        result = refresh_all_tokens()
        logger.info("Midnight token refresh: %s", result)
    except Exception as exc:
        logger.error("Midnight token refresh/log wipe failed: %s", exc)

def _schedule_jobs():
    global _scheduler
    if not _scheduler:
        return
    
    # Remove existing quran post jobs
    for job in _scheduler.get_jobs():
        if job.id.startswith("quran_post_"):
            _scheduler.remove_job(job.id)

    tz = pytz.timezone(config.TIMEZONE)
    schedule = get_setting("schedule", [
        {"time": "09:00", "qari": "random"},
        {"time": "12:30", "qari": "random"},
        {"time": "16:30", "qari": "random"},
        {"time": "21:00", "qari": "random"}
    ])

    for i, item in enumerate(schedule):
        time_str = item.get("time")
        qari = item.get("qari", "random")
        media_type = item.get("media_type", "web_video")
        prompt = item.get("prompt", "")
        audio_mode = item.get("audio_mode", "heavy")
        
        if not time_str:
            continue
            
        try:
            hour, minute = time_str.strip().split(":")
            trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone=tz)
            _scheduler.add_job(
                _job_wrapper,
                kwargs={
                    "qari": qari,
                    "media_type": media_type,
                    "prompt": prompt,
                    "audio_mode": audio_mode
                },
                trigger=trigger,
                id=f"quran_post_{i}_{time_str.replace(':', '')}",
                replace_existing=True,
                misfire_grace_time=300,  # 5 min grace window
            )
            logger.info("Scheduled post at %s (%s) with qari=%s, media=%s", time_str, config.TIMEZONE, qari, media_type)
        except Exception as exc:
            logger.error("Could not schedule post at %s: %s", time_str, exc)

def reload_scheduler():
    """Reloads job timings from DB."""
    logger.info("Reloading scheduler settings from database...")
    _schedule_jobs()

def start_scheduler() -> None:
    global _scheduler

    tz = pytz.timezone(config.TIMEZONE)
    _scheduler = BackgroundScheduler(timezone=tz)

    _schedule_jobs()

    # Daily midnight token refresh
    _scheduler.add_job(
        _token_refresh_wrapper,
        trigger=CronTrigger(hour=0, minute=0, timezone=tz),
        id="token_refresh_midnight",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("Scheduled daily token refresh at 00:00 (%s)", config.TIMEZONE)

    _scheduler.start()
    logger.info("Scheduler started with %d job(s)", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_scheduler_info() -> dict:
    if _scheduler is None:
        return {"running": False, "jobs": []}
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time),
        })
    return {"running": _scheduler.running, "jobs": jobs}
