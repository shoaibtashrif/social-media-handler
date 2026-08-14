"""
image_gen_service.py
Generates AI images using two free backends:
  1. Pollinations.ai  — no auth needed (uses POLLINATIONS_API_KEY if set for priority)
  2. HuggingFace Inference API — free tier with HF_TOKEN
Used for slide-style image posts. Video posts use user-uploaded images instead.
"""
import logging
import time
import requests
from pathlib import Path
from datetime import datetime

from app import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Pollinations.ai  (primary — no quota, always free)
# ─────────────────────────────────────────────────────────────

def generate_with_pollinations(prompt: str, width: int = 1080, height: int = 1080) -> bytes:
    """
    Generate an image via Pollinations.ai.
    Returns raw image bytes (PNG).
    """
    import urllib.parse

    encoded = urllib.parse.quote(prompt)
    # Add seed for reproducibility + nologo for clean output
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&nologo=true&model=flux"
    )
    logger.info("Pollinations request: %s", url[:120])
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    return resp.content


# ─────────────────────────────────────────────────────────────
# HuggingFace Inference API  (fallback)
# ─────────────────────────────────────────────────────────────

_HF_MODEL = "stabilityai/stable-diffusion-2-1"
_HF_API_URL = f"https://api-inference.huggingface.co/models/{_HF_MODEL}"


def generate_with_huggingface(prompt: str) -> bytes:
    """
    Generate an image via HuggingFace Inference API.
    Returns raw image bytes (JPEG/PNG).
    Raises RuntimeError if HF_TOKEN is not configured.
    """
    if not config.HF_TOKEN:
        raise RuntimeError("HF_TOKEN not set in .env — cannot use HuggingFace backend")

    headers = {"Authorization": f"Bearer {config.HF_TOKEN}"}
    payload = {"inputs": prompt, "parameters": {"width": 1024, "height": 1024}}

    for attempt in range(3):
        logger.info("HuggingFace request (attempt %d): %s", attempt + 1, prompt[:80])
        resp = requests.post(_HF_API_URL, headers=headers, json=payload, timeout=120)
        if resp.status_code == 503:
            # Model loading — wait and retry
            wait = 20 * (attempt + 1)
            logger.warning("HF model loading, waiting %ds…", wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.content

    raise RuntimeError("HuggingFace model unavailable after 3 attempts")


# ─────────────────────────────────────────────────────────────
# Unified generator with fallback
# ─────────────────────────────────────────────────────────────

def generate_image(prompt: str, save_to: Path | None = None) -> Path:
    """
    Generate an image. Tries Pollinations first, falls back to HuggingFace.
    Saves to save_to (or a temp path) and returns the Path.
    """
    if save_to is None:
        config.VIDEO_DIR.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_to = config.TEMP_DIR / "generated_images" / f"gen_{ts}.png"

    save_to.parent.mkdir(parents=True, exist_ok=True)

    img_bytes = None
    try:
        img_bytes = generate_with_pollinations(prompt)
        logger.info("Generated via Pollinations")
    except Exception as exc:
        logger.warning("Pollinations failed: %s — trying HuggingFace", exc)
        try:
            img_bytes = generate_with_huggingface(prompt)
            logger.info("Generated via HuggingFace")
        except Exception as exc2:
            raise RuntimeError(f"Both image backends failed: {exc} | {exc2}") from exc2

    save_to.write_bytes(img_bytes)
    logger.info("Image saved: %s", save_to)
    return save_to


# ─────────────────────────────────────────────────────────────
# Quran-themed prompt helpers
# ─────────────────────────────────────────────────────────────

QURAN_PROMPTS = [
    "serene mosque at golden hour, dramatic sky, photorealistic, cinematic lighting",
    "arabic calligraphy art, geometric patterns, dark background, golden ink",
    "peaceful desert landscape at sunset, dunes, warm orange sky, spiritual atmosphere",
    "night sky over Kaaba Mecca, stars, beautiful Islamic architecture, cinematic",
    "misty mountain at dawn, spiritual peaceful nature, warm light, no text",
    "ocean at sunrise, golden reflections, peaceful calm, spiritual photography",
    "rain falling on a mosque, reflections in water, soft lighting, cinematic",
    "ancient mosque at blue hour, minaret silhouette, stars visible, atmospheric",
]

import random as _random

def random_quran_prompt() -> str:
    return _random.choice(QURAN_PROMPTS)
