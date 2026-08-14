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

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _job_wrapper():
    """Wrapper so import happens at call time (avoids circular imports)."""
    from app.jobs.quran_video_job import run_quran_post_job
    try:
        run_quran_post_job()
    except Exception as exc:
        logger.error("Scheduled job failed: %s", exc)


def _token_refresh_wrapper():
    """Daily token refresh — runs at midnight."""
    from app.services.token_service import refresh_all_tokens
    try:
        result = refresh_all_tokens()
        logger.info("Midnight token refresh: %s", result)
    except Exception as exc:
        logger.error("Midnight token refresh failed: %s", exc)


def start_scheduler() -> None:
    global _scheduler

    tz = pytz.timezone(config.TIMEZONE)
    _scheduler = BackgroundScheduler(timezone=tz)

    post_times = config.POST_TIMES[: config.POSTS_PER_DAY]  # honour POSTS_PER_DAY cap
    if not post_times:
        logger.warning("POST_TIMES is empty — no scheduled posts will run")
        return

    for time_str in post_times:
        try:
            hour, minute = time_str.strip().split(":")
            trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone=tz)
            _scheduler.add_job(
                _job_wrapper,
                trigger=trigger,
                id=f"quran_post_{time_str.replace(':', '')}",
                replace_existing=True,
                misfire_grace_time=300,  # 5 min grace window
            )
            logger.info("Scheduled post at %s (%s)", time_str, config.TIMEZONE)
        except Exception as exc:
            logger.error("Could not schedule post at %s: %s", time_str, exc)

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
