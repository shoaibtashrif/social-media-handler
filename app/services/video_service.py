"""
video_service.py
Builds an MP4 from a static background image or a video + audio track using FFmpeg.
Output is 1080×1080 (Instagram-compatible) or vertical if you choose to adapt, H.264 + AAC.
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

NATURE_QUERIES = [
    "sunset aesthetic loop #shorts", "desert drone shot #shorts", "train passing by river loop #shorts",
    "rain drops on window #shorts", "rain in forest #shorts", "drone over ocean waves #shorts",
    "snow falling loop #shorts", "autumn leaves falling #shorts", "mountain stream flowing #shorts",
    "campfire burning loop #shorts", "stars night sky time lapse #shorts", "aurora borealis #shorts",
    "waterfall cinematic #shorts", "foggy forest drone #shorts", "cherry blossoms blowing #shorts",
    "underwater coral reef #shorts", "clouds moving time lapse #shorts", "moonlight on water #shorts",
    "sunrise over mountains #shorts", "golden hour wheat field #shorts", "ocean sunset #shorts",
    "city rain night aesthetic #shorts", "coffee shop rain window #shorts", "bamboo forest loop #shorts",
    "jungle waterfall #shorts", "river rapids #shorts", "galaxy space loop #shorts",
    "tropical beach drone #shorts", "storm clouds brewing #shorts", "lightning strike slow motion #shorts",
    "fireflies in forest #shorts", "winter wonderland #shorts", "glacier melting #shorts",
    "volcano eruption loop #shorts", "birds flying in slow motion #shorts", "hot air balloons cappadocia #shorts",
    "drone over canyon #shorts", "driving in the rain POV #shorts", "neon city rain aesthetic #shorts",
    "mist over lake #shorts", "sun rays through trees #shorts", "abstract water ripples #shorts",
    "sand dunes drone #shorts", "pine trees swaying #shorts", "cherry blossom petals falling #shorts",
    "aurora timelapse #shorts", "milky way timelapse #shorts", "ocean waves crashing #shorts",
    "rain on car window #shorts", "river running through rocks #shorts", "autumn road driving #shorts"
]

def pick_random_media(media_type: str = "any") -> Path:
    """
    Pick a random image or video from UPLOAD_MEDIA_DIR.
    media_type: 'image', 'video', or 'any'
    """
    patterns = []
    if media_type in ["image", "any"]:
        patterns.extend(["*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.JPEG", "*.PNG"])
    if media_type in ["video", "any"]:
        patterns.extend(["*.mp4", "*.mov", "*.MP4", "*.MOV"])
    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(config.UPLOAD_MEDIA_DIR.glob(pat))

    if not candidates:
        raise RuntimeError(
            f"No media found in {config.UPLOAD_MEDIA_DIR}. "
            "Please add .jpg/.png/.mp4 files to upload_media/"
        )
    chosen = random.choice(candidates)
    logger.info("Selected background media: %s", chosen.name)
    return chosen


def _get_duration(path: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    return float(subprocess.check_output(cmd).decode().strip())

def fetch_web_video(target_duration: int = 50) -> Path:
    """
    Downloads random copyright-free nature videos from Pexels API to create a 
    background video long enough to cover 'target_duration' seconds.
    Each clip is ~5s. We need ceil(target_duration/5) clips.
    Scenes change every 5 seconds for a dynamic reel look.
    """
    import requests
    
    config.VIDEO_DIR.parent.mkdir(parents=True, exist_ok=True)
    out_path = config.TEMP_DIR / "downloaded_web_video.mp4"
    if out_path.exists():
        out_path.unlink()

    pexel_key = config.PEXELS_API_KEY
    if not pexel_key:
        logger.warning("PEXELS_API_KEY not found in .env! Falling back to local upload_media/")
        return pick_random_media("video")

    clips_needed = max(3, (target_duration + 4) // 5)
    logger.info("Need %d Pexels clips to cover %ds...", clips_needed, target_duration)

    clips = []
    used_queries = set()
    
    # Clean queries without youtube hashtags
    PEXELS_QUERIES = [
        "sunset aesthetic", "desert drone", "train passing by river",
        "rain drops window", "rain forest", "drone ocean waves",
        "snow falling", "autumn leaves falling", "mountain stream",
        "campfire burning", "stars night sky lapse", "aurora borealis",
        "clouds moving fast", "city lights night drone", "calm ocean"
    ]
    
    for i in range(clips_needed):
        remaining_queries = [q for q in PEXELS_QUERIES if q not in used_queries]
        if not remaining_queries:
            remaining_queries = PEXELS_QUERIES
        q = random.choice(remaining_queries)
        used_queries.add(q)

        clip_path = config.TEMP_DIR / f"clip_{i}.mp4"
        if clip_path.exists():
            clip_path.unlink()

        logger.info("Fetching clip %d/%d from Pexels: '%s'", i+1, clips_needed, q)
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": pexel_key},
                params={"query": q, "per_page": 15, "orientation": "portrait", "size": "medium"},
                timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("videos"):
                logger.warning("No Pexels videos found for '%s'", q)
                continue
                
            video = random.choice(data["videos"])
            # Get video file with portrait resolution closest to 1080x1920
            video_files = [f for f in video["video_files"] if f.get("file_type") == "video/mp4"]
            if not video_files:
                continue
                
            # Sort by height to get the best quality available
            video_files.sort(key=lambda x: x.get("height", 0), reverse=True)
            best_link = video_files[0]["link"]
            
            # Download and trim to 5 seconds
            cmd = [
                "ffmpeg", "-y", "-i", best_link,
                "-t", "5",
                "-c", "copy",
                str(clip_path)
            ]
            subprocess.run(cmd, capture_output=True)
            
            if clip_path.exists() and clip_path.stat().st_size > 1000:
                clips.append(clip_path)
        except Exception as exc:
            logger.error("Failed to fetch Pexels video: %s", exc)

    if not clips:
        logger.error("Failed to download any Pexels video clips. Falling back to local media.")
        return pick_random_media("video")

    if len(clips) == 1:
        logger.warning("Only 1 clip downloaded — returning as-is.")
        return clips[0]

    # Concatenate all clips into one long background video
    concat_filter = ""
    inputs = []
    for i, clip in enumerate(clips):
        inputs.extend(["-i", str(clip)])
        concat_filter += (
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
            f"setpts=PTS-STARTPTS[v{i}]; "
        )

    concat_filter += "".join([f"[v{i}]" for i in range(len(clips))])
    concat_filter += f"concat=n={len(clips)}:v=1:a=0[vout]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", concat_filter,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        str(out_path)
    ]
    logger.info("Concatenating %d clips (%ds total background)...", len(clips), len(clips)*5)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if not out_path.exists() or out_path.stat().st_size < 1000:
        logger.error("Concat failed: %s — using single clip.", result.stderr[-300:])
        return clips[0]

    return out_path

def build_video(
    audio_path: Path,
    media_path: Path | None = None,
    media_type: str = "any",
    audio_mode: str = "heavy",  # "heavy", "minor", or "original"
) -> Path:
    """
    Create a 1080x1920 (9:16 Reels) MP4 from a background (image or video) + audio.
    audio_mode:
      heavy    — slow 0.75x + reverb + background rain (default, for Alafasy etc.)
      minor    — slight slow 0.9x + very soft rain only (for Othman / Mossad)
      original — no audio processing, just mix with very soft background rain
    Returns the path to the output video file.
    """
    if media_path is None:
        media_path = pick_random_media(media_type)

    config.VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = config.VIDEO_DIR / f"quran_reel_{timestamp}.mp4"

    is_video = media_path.suffix.lower() in [".mp4", ".mov"]
    rain_path = str(Path("assets/rain.mp3").absolute())

    # Audio filter chain based on mode
    if audio_mode == "heavy":
        # Slow 0.75x, reverb, moderate rain background
        audio_filter = (
            "[2:a]volume=0.15[rain];"
            "[1:a]asetrate=44100*0.75,aresample=44100,aecho=0.8:0.85:600:0.2[voice];"
            "[voice][rain]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    elif audio_mode == "minor":
        # Slight slow 0.9x, tiny echo, very soft rain
        audio_filter = (
            "[2:a]volume=0.07[rain];"
            "[1:a]asetrate=44100*0.90,aresample=44100,aecho=0.6:0.5:300:0.08[voice];"
            "[voice][rain]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    else:  # original
        # No processing, just a barely audible nature background
        audio_filter = (
            "[2:a]volume=0.04[rain];"
            "[1:a]acopy[voice];"
            "[voice][rain]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )

    # Video visual filter (applied to all modes for copyright bypass)
    vid_filter_video = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        "hflip,eq=contrast=1.1:brightness=0.02:saturation=1.2,vignette[vout]"
    )

    # Calc duration — heavy mode slows audio by 0.75, minor by 0.9
    audio_dur = _get_duration(audio_path)
    speed_factor = {"heavy": 0.75, "minor": 0.90, "original": 1.0}.get(audio_mode, 0.75)
    # The actual output duration after speed change
    target_dur = min((audio_dur / speed_factor) + 1.0, 58.0)  # hard cap at 58s

    if is_video:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(media_path),
            "-i", str(audio_path),
            "-stream_loop", "-1", "-i", rain_path,
            "-filter_complex",
            audio_filter + ";" + vid_filter_video,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-r", "25",
            "-t", str(target_dur),
            str(out_path),
        ]
    else:
        zoompan_frames = int(target_dur * 25)
        vid_filter_image = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='zoom+0.0005':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={zoompan_frames}:s=1080x1920:fps=25,"
            f"hflip,eq=contrast=1.1:brightness=0.02:saturation=1.2,vignette[vout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(media_path),
            "-i", str(audio_path),
            "-stream_loop", "-1", "-i", rain_path,
            "-filter_complex",
            audio_filter + ";" + vid_filter_image,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-r", "25",
            "-t", str(target_dur),
            str(out_path),
        ]

    logger.info("Building video: %s (is_video=%s, audio_mode=%s, dur=%.1fs)", out_path.name, is_video, audio_mode, target_dur)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("FFmpeg video error:\n%s", result.stderr[-600:])
        raise RuntimeError(f"FFmpeg video build failed: {result.stderr[-200:]}")

    size_mb = out_path.stat().st_size / (1024 * 1024)
    logger.info("Video ready: %s (%.1f MB)", out_path.name, size_mb)
    return out_path
