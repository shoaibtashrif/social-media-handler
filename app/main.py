"""
main.py — FastAPI application entry point.
Starts the scheduler on startup, registers all routers.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import health, media, post, token
from app.services import scheduler_service, token_service

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("🕌  Quran Social Media Automation starting …")
    logger.info("Tunnel URL : %s", config.TUNNEL_URL or "(not set)")
    logger.info("Post times : %s (%s)", config.POST_TIMES, config.TIMEZONE)
    logger.info("Reciters   : %s", [q["name"] for q in config.QARIS])
    logger.info("Media dir  : %s", config.UPLOAD_MEDIA_DIR)
    logger.info("=" * 60)

    # ── Auto-manage tokens on startup ───────────────────────
    logger.info("🔑  Checking / refreshing API tokens …")
    try:
        tok_result = token_service.refresh_all_tokens()
        if tok_result.get("ig_refreshed"):
            logger.info("✅ IG token refreshed. New expiry: %s", tok_result.get("ig_new_expiry"))
        if tok_result.get("fb_token_fetched"):
            logger.info("✅ FB page token fetched for: %s", tok_result.get("fb_page_name"))
        if tok_result.get("errors"):
            for err in tok_result["errors"]:
                logger.warning("Token warning: %s", err)
    except Exception as exc:
        logger.warning("Token refresh skipped (will retry at midnight): %s", exc)

    scheduler_service.start_scheduler()
    yield
    scheduler_service.stop_scheduler()
    logger.info("Shutdown complete.")


# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="Quran Social Media Automation",
    description=(
        "Automated Quran content poster — downloads copyright-free Quran audio, "
        "builds videos with FFmpeg, and posts to Instagram + Facebook on a schedule."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(media.router)
app.include_router(post.router)
app.include_router(token.router)


@app.get("/", tags=["root"])
def root():
    return {
        "service": "Quran Social Media Automation",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "post_now_async": "POST /api/post-now",
            "post_now_sync": "POST /api/post-now/sync",
            "status": "GET /api/status",
            "config": "GET /api/verse-pool",
            "serve_media": "GET /media/{filename}",
            "token_status": "GET /api/token-status",
            "refresh_token": "POST /api/refresh-token",
            "docs": "/docs",
        },
        "tunnel": config.TUNNEL_URL or "NOT SET — update TUNNEL_URL in .env",
    }
