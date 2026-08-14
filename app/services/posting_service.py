"""
posting_service.py
Posts content to Instagram and Facebook using the Meta Graph API.

Instagram flow (video):
  1. Create container  →  POST /{ig_user_id}/media  (video_url = public URL)
  2. Poll until FINISHED
  3. Publish            →  POST /{ig_user_id}/media_publish

Facebook flow (video):
  POST /{page_id}/videos  with file_url + description

Both use tokens from .env — zero hardcoded values.
"""
import logging
import time
import requests
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app import config

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v20.0"


# ─────────────────────────────────────────────────────────────
# Instagram
# ─────────────────────────────────────────────────────────────

def post_instagram_video(video_url: str, caption: str) -> str | None:
    """
    Upload a video reel to Instagram.
    Returns the media ID on success, None on failure.
    """
    token = config.INSTAGRAM_API
    uid = config.INSTAGRAM_USER_ID

    # Step 1: Create container
    logger.info("IG: Creating video container …")
    resp = requests.post(
        f"{GRAPH_BASE}/{uid}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
        timeout=60,
    )
    data = resp.json()
    if "error" in data:
        logger.error("IG container error: %s", data["error"])
        return None
    container_id = data.get("id")
    if not container_id:
        logger.error("IG container: no ID returned: %s", data)
        return None
    logger.info("IG container created: %s", container_id)

    # Step 2: Wait for video to be processed by Meta
    media_id = _wait_for_container(container_id, token)
    if not media_id:
        return None

    # Step 3: Publish
    logger.info("IG: Publishing container %s …", media_id)
    pub_resp = requests.post(
        f"{GRAPH_BASE}/{uid}/media_publish",
        params={"creation_id": media_id, "access_token": token},
        timeout=60,
    )
    pub_data = pub_resp.json()
    if "error" in pub_data:
        logger.error("IG publish error: %s", pub_data["error"])
        return None

    post_id = pub_data.get("id")
    logger.info("✅ Instagram posted: %s", post_id)
    return post_id


def _wait_for_container(container_id: str, token: str, max_wait: int = 300) -> str | None:
    """Poll until container status is FINISHED (up to max_wait seconds)."""
    waited = 0
    while waited < max_wait:
        resp = requests.get(
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        data = resp.json()
        status = data.get("status_code", "")
        logger.debug("IG container %s status: %s", container_id, status)

        if status == "FINISHED":
            return container_id
        elif status in ("ERROR", "EXPIRED"):
            logger.error("IG container %s failed: %s", container_id, data.get("status"))
            return None

        time.sleep(10)
        waited += 10

    logger.error("IG container %s timed out after %ds", container_id, max_wait)
    return None


# ─────────────────────────────────────────────────────────────
# Facebook
# ─────────────────────────────────────────────────────────────

def post_facebook_video(video_url: str, description: str) -> str | None:
    """
    Post a video to the Facebook Page.
    Returns the post ID on success, None on failure.
    """
    token = config.FACEBOOK_PAGE_TOKEN
    page_id = config.FACEBOOK_PAGE_ID

    logger.info("FB: Posting video to page %s …", page_id)
    resp = requests.post(
        f"{GRAPH_BASE}/{page_id}/videos",
        params={
            "file_url": video_url,
            "description": description,
            "published": "true",
            "access_token": token,
        },
        timeout=120,
    )
    data = resp.json()
    if "error" in data:
        logger.error("FB post error: %s", data["error"])
        return None

    post_id = data.get("id")
    logger.info("✅ Facebook posted: %s", post_id)
    return post_id


# ─────────────────────────────────────────────────────────────
# YouTube
# ─────────────────────────────────────────────────────────────

def post_youtube_shorts(video_path: str, title: str, description: str) -> str | None:
    """
    Upload a video to YouTube as a Short.
    Returns the video ID on success, None on failure.
    Requires youtube_token.json to be present in the project root.
    """
    token_path = "youtube_token.json"
    if not os.path.exists(token_path):
        logger.error("YT: %s not found. Run youtube_auth.py first.", token_path)
        return None

    logger.info("YT: Uploading video to YouTube Shorts …")
    try:
        creds = Credentials.from_authorized_user_file(token_path, ["https://www.googleapis.com/auth/youtube.upload"])
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

        # Truncate title to 100 chars (YouTube limit)
        if len(title) > 100:
            title = title[:97] + "..."

        request_body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["quran", "islam", "shorts", "recitation"],
                "categoryId": "22", # People & Blogs
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            }
        }

        media_file = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media_file
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.debug("YT Upload progress: %d%%", int(status.progress() * 100))
        
        video_id = response.get("id")
        logger.info("✅ YouTube posted: %s", video_id)
        return video_id

    except Exception as exc:
        logger.error("YT upload failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────
# Combined poster
# ─────────────────────────────────────────────────────────────

def post_to_all(video_url: str, video_path: str, caption: str) -> dict:
    """
    Post to Instagram, Facebook, and YouTube.
    Returns dict with ig_post_id, fb_post_id, and yt_post_id.
    """
    logger.info("Posting to Instagram, Facebook, and YouTube …")
    
    # Extract title from caption for YouTube
    yt_title = caption.split('\n')[0]
    # Ensure #Shorts is in the description
    yt_desc = caption + "\n\n#Shorts #Quran"

    ig_id = post_instagram_video(video_url, caption)
    fb_id = post_facebook_video(video_url, caption)
    yt_id = post_youtube_shorts(video_path, yt_title, yt_desc)

    return {"ig_post_id": ig_id, "fb_post_id": fb_id, "yt_post_id": yt_id}

