"""
quran_video_job.py
Main automation job:
  1. Pick next Qari (rotating via tracker)
  2. Pick a random verse range from VERSE_POOL
  3. Download + concatenate verse MP3s from EveryAyah
  4. Pick a random image from upload_media/
  5. Build 1080×1080 MP4 with FFmpeg
  6. Post to Instagram + Facebook via tunnel URL
  7. Log result to CSV
"""
import logging
import random
import os

from app import config
from app.services import audio_service, video_service, posting_service, image_gen_service
from app.jobs import post_tracker

logger = logging.getLogger(__name__)


def run_quran_post_job(
    qari_index: int | None = None,
    media_type: str = "any",
    ai_prompt: str | None = None,
    audio_mode: str = "heavy",  # "heavy", "minor", or "original"
) -> dict:
    """
    Execute one full post cycle.
    Returns a result dict with status, post IDs, and details.
    """
    logger.info("═" * 60)
    logger.info("🕌 Starting Quran post job …")

    try:
        # ── 1. Pick Qari ─────────────────────────────────────
        if qari_index is None:
            qari_idx = post_tracker.get_next_qari_index(len(config.QARIS))
        else:
            qari_idx = qari_index
            
        qari = config.QARIS[qari_idx]
        reciter_name = qari["name"]
        reciter_folder = qari["folder"]
        is_youtube = qari.get("is_youtube", False)
        logger.info("🎙️  Reciter: %s (%s)", reciter_name, reciter_folder)

        # ── 3. Pick duration ──────────────────────────────────
        target_duration = random.randint(config.MIN_DURATION, config.MAX_DURATION)
        logger.info("⏱️   Target duration: %ds", target_duration)

        # ── 2 & 4. Download + build audio ─────────────────────
        if is_youtube:
            surah = 0
            start_ayah = 0
            end_ayah = 0
            surah_name = "Beautiful Recitation"
            logger.info("📖  Fetching from archive.org directly")
            audio_path = audio_service.fetch_archive_qari_chunk(reciter_name, target_duration)
        else:
            if not config.VERSE_POOL:
                raise RuntimeError("VERSE_POOL is empty — check .env")
            surah, start_ayah, end_ayah = random.choice(config.VERSE_POOL)
            surah_name = config.SURAH_NAMES.get(surah, f"Surah {surah}")
            logger.info("📖  %s (%d:%d–%d)", surah_name, surah, start_ayah, end_ayah)

            audio_path = audio_service.build_audio_clip(
                reciter_folder=reciter_folder,
                surah=surah,
                start_ayah=start_ayah,
                end_ayah=end_ayah,
                target_duration=target_duration,
            )
            
        logger.info("🎵  Audio ready: %s", audio_path.name)

        # ── 5. Build video ────────────────────────────────────
        if media_type == "ai" and ai_prompt:
            logger.info("🤖 Generating AI image background...")
            media_path = image_gen_service.generate_image(prompt=ai_prompt)
        elif media_type == "web_video":
            logger.info("🌍 Downloading copyright-free background video (multi-clip)...")
            media_path = video_service.fetch_web_video(target_duration=target_duration)
        else:
            media_path = video_service.pick_random_media(media_type)

        video_path = video_service.build_video(
            audio_path=audio_path,
            media_path=media_path,
            audio_mode=audio_mode,
        )
        logger.info("🎬  Video ready: %s", video_path.name)

        # ── 6. Construct public URL ───────────────────────────
        if not config.TUNNEL_URL:
            raise RuntimeError("TUNNEL_URL not set in .env — Instagram needs a public URL")
        public_url = f"{config.TUNNEL_URL}/media/{video_path.name}"
        logger.info("🌐  Public URL: %s", public_url)

        # ── 7. Build caption ──────────────────────────────────
        caption = _build_caption(surah, surah_name, start_ayah, end_ayah, reciter_name)

        # ── 8. Post ───────────────────────────────────────────
        result = posting_service.post_to_all(
            video_url=public_url,
            video_path=str(video_path),
            caption=caption,
        )
        ig_id = result["ig_post_id"]
        fb_id = result["fb_post_id"]
        yt_id = result.get("yt_post_id")

        status = "success" if (ig_id or fb_id or yt_id) else "failed"

        # ── 9. Log ────────────────────────────────────────────
        # ── 9. Log ────────────────────────────────────────────
        post_tracker.log_post(
            reciter=reciter_name,
            surah=surah,
            surah_name=surah_name,
            start_ayah=start_ayah,
            end_ayah=end_ayah,
            duration_s=target_duration,
            video_file=video_path.name,
            video_url=public_url,
            ig_post_id=ig_id,
            fb_post_id=fb_id,
            status=status,
            notes=f"media={media_path.name if media_path else ''} yt={yt_id}",
        )

        logger.info(
            "✅ Job done — %s | IG: %s | FB: %s | YT: %s",
            status, ig_id or "❌", fb_id or "❌", yt_id or "❌",
        )

        return {
            "status": status,
            "reciter": reciter_name,
            "surah": surah_name,
            "verses": f"{start_ayah}-{end_ayah}",
            "duration_s": target_duration,
            "video": video_path.name,
            "public_url": public_url,
            "ig_post_id": ig_id,
            "fb_post_id": fb_id,
            "yt_post_id": yt_id,
        }

    except Exception as exc:
        logger.exception("❌ Job failed: %s", exc)
        try:
            post_tracker.log_post(
                reciter="ERROR", surah=0, surah_name="", start_ayah=0, end_ayah=0,
                duration_s=0, video_file="", video_url="",
                ig_post_id=None, fb_post_id=None,
                status="error", notes=str(exc)[:200],
            )
        except Exception:
            pass
        raise

    finally:
        # ── 10. Robust Cleanup ────────────────────────────────────────
        # This ALWAYS runs, even if the job crashed with an exception.
        import os
        import shutil
        try:
            if audio_path and audio_path.exists():
                os.remove(audio_path)
            if video_path and video_path.exists():
                os.remove(video_path)
            # We don't delete media_path if it's from upload_media/, only if it's in temp
            if media_path and media_path.exists() and "temp" in str(media_path):
                os.remove(media_path)
                
            # Aggressively wipe the generic temp directories (not the cached folders)
            # The temp video folder only contains output reels.
            for item in config.VIDEO_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                    
            logger.info("🧹 Cleaned up junk audio/video files")
        except Exception as e:
            logger.error("Failed to clean up junk files: %s", e)


# ─────────────────────────────────────────────────────────────
# Caption builder
# ─────────────────────────────────────────────────────────────

def _build_caption(surah: int, surah_name: str, start: int, end: int, reciter: str) -> str:
    if surah == 0:
        return (
            f"✨ {surah_name}\n\n"
            f"🎙️ Reciter: {reciter}\n"
            f"🤲 May Allah accept this from us\n\n"
            f"#Quran #QuranRecitation #IslamicContent\n"
            f"#QuranReels #QuranVerse #SpiritualContent\n"
            f"#Islam #Muslims #DailyQuran #QuranDaily"
        )
        
    tag_name = surah_name.replace("'", "").replace("-", "").replace(" ", "")
    return (
        f"✨ {surah_name} | Surah {surah}: {start}–{end}\n\n"
        f"🎙️ Reciter: {reciter}\n"
        f"🤲 May Allah accept this from us\n\n"
        f"🎧 Audio provided by Copyright Free Quran\n"
        f"🔗 https://sites.google.com/view/copyrightfreequran\n\n"
        f"#Quran #QuranRecitation #{tag_name} #IslamicContent\n"
        f"#QuranReels #Surah{surah} #QuranVerse #SpiritualContent\n"
        f"#Islam #Muslims #DailyQuran #QuranDaily"
    )
