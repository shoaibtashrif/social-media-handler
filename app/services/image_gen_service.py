"""
image_gen_service.py
Generates AI images using a 3-tier fallback chain:
  1. Cloudflare Workers AI (FLUX.1-schnell)
  2. HuggingFace Inference API (FLUX.1-schnell)
  3. Pollinations.ai (Flux)
"""
import logging
import time
import requests
import urllib.parse
import base64
from pathlib import Path
from datetime import datetime

from app import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1. Cloudflare Workers AI (FLUX.1-schnell)
# ─────────────────────────────────────────────────────────────
def generate_with_cloudflare(prompt: str) -> bytes | None:
    if not config.CF_API_TOKEN or not config.CF_ACCOUNT_ID:
        logger.warning("No CF_API_TOKEN or CF_ACCOUNT_ID, skipping Cloudflare.")
        return None

    logger.info("Generating via Cloudflare FLUX schnell...")
    url = f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {
        "Authorization": f"Bearer {config.CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            img_b64 = data["result"]["image"]
            return base64.b64decode(img_b64)
        else:
            logger.warning("Cloudflare error: %s", data.get("errors", "unknown"))
            return None
    except Exception as e:
        logger.warning("Cloudflare failed: %s", e)
        return None


# ─────────────────────────────────────────────────────────────
# 2. HuggingFace Inference API (FLUX.1-schnell)
# ─────────────────────────────────────────────────────────────
_HF_MODEL = "black-forest-labs/FLUX.1-schnell"
_HF_API_URL = f"https://api-inference.huggingface.co/models/{_HF_MODEL}"

def generate_with_huggingface(prompt: str) -> bytes | None:
    if not config.HF_TOKEN:
        logger.warning("No HF_TOKEN found, skipping HuggingFace.")
        return None

    logger.info("Generating via HuggingFace FLUX schnell...")
    headers = {"Authorization": f"Bearer {config.HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"width": 1024, "height": 1024},
        "options": {"use_cache": False}
    }

    try:
        for attempt in range(3):
            resp = requests.post(_HF_API_URL, headers=headers, json=payload, timeout=120)
            if resp.status_code == 503:
                wait = 20 * (attempt + 1)
                logger.warning("HF model loading, waiting %ds…", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.content
        logger.warning("HuggingFace model unavailable after 3 attempts")
        return None
    except Exception as e:
        logger.warning("HuggingFace failed: %s", e)
        return None


# ─────────────────────────────────────────────────────────────
# 3. Pollinations.ai (Flux)
# ─────────────────────────────────────────────────────────────
def generate_with_pollinations(prompt: str, width: int = 1080, height: int = 1080) -> bytes | None:
    logger.info("Generating via Pollinations FLUX...")
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&model=flux"
    
    try:
        resp = requests.get(url, timeout=90)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.warning("Pollinations failed: %s", e)
        return None


# ─────────────────────────────────────────────────────────────
# Unified generator with 3-tier fallback
# ─────────────────────────────────────────────────────────────
def generate_image(prompt: str, save_to: Path | None = None) -> Path:
    """
    Fallback chain: Cloudflare -> HuggingFace -> Pollinations
    """
    if save_to is None:
        config.VIDEO_DIR.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_to = config.TEMP_DIR / "generated_images" / f"gen_{ts}.png"

    save_to.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try Cloudflare
    img_bytes = generate_with_cloudflare(prompt)
    
    # 2. Try HuggingFace
    if not img_bytes:
        img_bytes = generate_with_huggingface(prompt)
        
    # 3. Try Pollinations
    if not img_bytes:
        img_bytes = generate_with_pollinations(prompt)

    if not img_bytes:
        raise RuntimeError("All 3 image backends (CF, HF, Pollinations) failed.")

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
