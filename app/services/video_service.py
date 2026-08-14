"""
video_service.py
Builds an MP4 from a static background image + audio track using FFmpeg.
Output is 1080×1080 (Instagram-compatible), H.264 + AAC.
"""
import subprocess
import logging
import random
from datetime import datetime
from pathlib import Path

from app import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def pick_random_image() -> Path:
    """
    Pick a random image from UPLOAD_MEDIA_DIR.
    Supports .jpg / .jpeg / .png / .webp
    """
    patterns = ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.JPEG", "*.PNG"]
    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(config.UPLOAD_MEDIA_DIR.glob(pat))

    if not candidates:
        raise RuntimeError(
            f"No images found in {config.UPLOAD_MEDIA_DIR}. "
            "Please add .jpg/.png files to upload_media/"
        )
    chosen = random.choice(candidates)
    logger.info("Selected background image: %s", chosen.name)
    return chosen


def build_video(audio_path: Path, image_path: Path | None = None) -> Path:
    """
    Create a 1080×1080 MP4 from a static image + audio.
    Returns the path to the output video file.
    """
    if image_path is None:
        image_path = pick_random_image()

    config.VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = config.VIDEO_DIR / f"quran_reel_{timestamp}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),   # static image, looped
        "-i", str(audio_path),                  # audio track
        "-c:v", "libx264",
        "-tune", "stillimage",                  # optimise for static frame
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",                  # max compatibility
        "-shortest",                            # stop when audio ends
        "-r", "25",                             # 25 fps
        "-vf",
        # Force 1080×1080 with black padding to preserve aspect ratio
        "scale=1080:1080:force_original_aspect_ratio=decrease,"
        "pad=1080:1080:(ow-iw)/2:(oh-ih)/2:black",
        str(out_path),
    ]

    logger.info("Building video: %s", out_path.name)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("FFmpeg video error:\n%s", result.stderr[-600:])
        raise RuntimeError(f"FFmpeg video build failed: {result.stderr[-200:]}")

    size_mb = out_path.stat().st_size / (1024 * 1024)
    logger.info("Video ready: %s (%.1f MB)", out_path.name, size_mb)
    return out_path
