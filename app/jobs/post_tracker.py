"""
post_tracker.py
CSV-based tracker that logs every post attempt (success or failure).
Tracker file path is set in config.TRACKER_CSV.
"""
import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from app import config

logger = logging.getLogger(__name__)

_HEADERS = [
    "date", "time", "reciter", "surah_number", "surah_name",
    "start_ayah", "end_ayah", "duration_s", "video_file",
    "video_url", "ig_post_id", "fb_post_id", "status", "notes",
]


def _ensure_tracker():
    path = config.TRACKER_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(_HEADERS)


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
    status: str = "success",
    notes: str = "",
) -> None:
    _ensure_tracker()
    now = datetime.now()
    row = [
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        reciter,
        surah,
        surah_name,
        start_ayah,
        end_ayah,
        round(duration_s, 1),
        video_file,
        video_url,
        ig_post_id or "failed",
        fb_post_id or "failed",
        status,
        notes,
    ]
    with open(config.TRACKER_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)
    logger.info("Tracker updated: surah=%s ayah=%s-%s ig=%s fb=%s", surah, start_ayah, end_ayah, ig_post_id, fb_post_id)


def get_recent_posts(n: int = 20) -> list[dict]:
    _ensure_tracker()
    rows = []
    with open(config.TRACKER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows[-n:]


# ── Qari rotation state ───────────────────────────────────────

def get_next_qari_index() -> int:
    state = _load_rotation()
    idx = state.get("next_qari_index", 0) % len(config.QARIS)
    state["next_qari_index"] = (idx + 1) % len(config.QARIS)
    _save_rotation(state)
    return idx


def _load_rotation() -> dict:
    path = config.ROTATION_STATE
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"next_qari_index": 0}


def _save_rotation(state: dict) -> None:
    config.ROTATION_STATE.parent.mkdir(parents=True, exist_ok=True)
    config.ROTATION_STATE.write_text(json.dumps(state, indent=2))
