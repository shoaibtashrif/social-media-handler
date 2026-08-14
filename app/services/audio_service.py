"""
audio_service.py
Downloads individual verse MP3s from EveryAyah.com (free, no API key).
Concatenates the requested verse range and trims/loops to target duration.
"""
import os
import subprocess
import logging
from pathlib import Path
import requests

from app import config

logger = logging.getLogger(__name__)

EVERYAYAH_BASE = "https://everyayah.com/data"


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def get_verse_url(reciter_folder: str, surah: int, ayah: int) -> str:
    """Return direct MP3 URL for a single verse from EveryAyah."""
    return f"{EVERYAYAH_BASE}/{reciter_folder}/{surah:03d}{ayah:03d}.mp3"


def download_verse(reciter_folder: str, surah: int, ayah: int) -> Path:
    """
    Download a single verse MP3 and cache it locally.
    Returns the local path.
    """
    dest_dir = config.AUDIO_DIR / reciter_folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{surah:03d}{ayah:03d}.mp3"

    if dest.exists() and dest.stat().st_size > 1000:
        logger.debug("Cache hit: %s", dest)
        return dest

    url = get_verse_url(reciter_folder, surah, ayah)
    logger.info("Downloading %s", url)
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        logger.info("Saved %s (%d bytes)", dest, len(resp.content))
    except Exception as exc:
        logger.error("Failed to download %s: %s", url, exc)
        raise

    return dest


def build_audio_clip(
    reciter_folder: str,
    surah: int,
    start_ayah: int,
    end_ayah: int,
    target_duration: int,
) -> Path:
    """
    Download verses start_ayah→end_ayah, concatenate them,
    then trim / loop to exactly target_duration seconds.
    Returns path to the final MP3.
    """
    # 1. Download each verse
    verse_files: list[Path] = []
    for ayah in range(start_ayah, end_ayah + 1):
        try:
            path = download_verse(reciter_folder, surah, ayah)
            verse_files.append(path)
        except Exception as exc:
            logger.warning("Skipping verse %d:%d — %s", surah, ayah, exc)

    if not verse_files:
        raise RuntimeError(f"No verse files downloaded for {surah}:{start_ayah}-{end_ayah}")

    # 2. Concatenate
    concat_path = _concat_mp3s(reciter_folder, surah, start_ayah, end_ayah, verse_files)

    # 3. Trim / loop to target duration
    trimmed_path = _trim_or_loop(concat_path, target_duration)
    return trimmed_path


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _concat_mp3s(
    reciter_folder: str,
    surah: int,
    start: int,
    end: int,
    files: list[Path],
) -> Path:
    """Concatenate MP3 files using FFmpeg concat demuxer (lossless, no re-encode)."""
    out_dir = config.AUDIO_DIR / "concat"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{reciter_folder}_{surah:03d}_{start:03d}_{end:03d}.mp3"

    if out_path.exists() and out_path.stat().st_size > 1000:
        return out_path

    list_file = out_dir / f"list_{reciter_folder}_{surah}_{start}_{end}.txt"
    list_file.write_text("\n".join(f"file '{f}'" for f in files))

    _run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path),
    ], label="concat")

    return out_path


def _get_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    raw = result.stdout.strip()
    if not raw:
        raise RuntimeError(f"Cannot get duration for {path}")
    return float(raw)


def _trim_or_loop(src: Path, target: int) -> Path:
    """
    Trim or loop an MP3 to exactly `target` seconds.
    Everything stays pure MP3 (-c copy). The video builder re-encodes to AAC
    when muxing image+audio, so we never need to transcode here.
    Uses -stream_loop for looping (avoids the concat-demuxer + AAC encoder bug).
    """
    out_dir = config.AUDIO_DIR / "trimmed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src.stem}_{target}s.mp3"

    if out_path.exists() and out_path.stat().st_size > 1000:
        return out_path

    actual = _get_duration(src)
    logger.info("Audio src=%.1fs  target=%ds", actual, target)

    if actual >= target:
        # Simple trim — stream copy, no re-encode
        _run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(src),
            "-t", str(target),
            "-c", "copy",
            str(out_path),
        ], label="trim")
    else:
        # Loop then trim — -stream_loop avoids the concat-demuxer + AAC bug
        loops = int(target / actual) + 2
        _run_ffmpeg([
            "ffmpeg", "-y",
            "-stream_loop", str(loops),
            "-i", str(src),
            "-t", str(target),
            "-c", "copy",
            str(out_path),
        ], label="stream_loop")

    return out_path


def _run_ffmpeg(cmd: list[str], label: str = "") -> None:
    logger.info("[ffmpeg:%s] %s", label, " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("[ffmpeg:%s] stderr: %s", label, result.stderr[-500:])
        raise RuntimeError(f"FFmpeg {label} failed: {result.stderr[-200:]}")
