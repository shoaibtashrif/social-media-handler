"""
token_service.py
Automatically manages Meta API tokens so you never have to touch them manually.

Instagram long-lived token:
  - Valid for 60 days
  - Can be refreshed anytime it's at least 1 day old
  - Endpoint: GET /oauth/access_token?grant_type=fb_exchange_token&...
  - Refreshed result is written back to .env

Facebook Page Access Token:
  - Never expires (if page token from long-lived user token)
  - Fetched from: GET /{page_id}?fields=access_token&access_token={user_token}
  - Also written to .env

Runs:
  - Once on startup
  - Daily at midnight via scheduler
  - On-demand via GET /api/refresh-token
"""
import logging
import os
import re
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

from app import config

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v20.0"
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


# ─────────────────────────────────────────────────────────────
# Main entry point (called on startup + scheduled)
# ─────────────────────────────────────────────────────────────

def refresh_all_tokens() -> dict:
    """
    1. Refresh Instagram long-lived user token if expiring within 30 days (or expired)
    2. Fetch / update Facebook Page Access Token from user token
    Returns summary dict.
    """
    result = {"ig_refreshed": False, "fb_token_fetched": False, "errors": []}

    # Step 1: Refresh IG user token
    try:
        ig_result = _refresh_instagram_token()
        result.update(ig_result)
    except Exception as exc:
        msg = f"IG token refresh failed: {exc}"
        logger.error(msg)
        result["errors"].append(msg)

    # Step 2: Get FB page token (uses whatever IG token we now have)
    try:
        fb_result = _fetch_facebook_page_token()
        result.update(fb_result)
    except Exception as exc:
        msg = f"FB page token fetch failed: {exc}"
        logger.error(msg)
        result["errors"].append(msg)

    return result


# ─────────────────────────────────────────────────────────────
# Instagram token refresh
# ─────────────────────────────────────────────────────────────

def _refresh_instagram_token() -> dict:
    """
    Refresh the Instagram long-lived user token.
    Meta allows refreshing any time the token is > 1 day old.
    New expiry = 60 days from now.
    """
    expiry_str = os.getenv("INSTAGRAM_TOKEN_EXPIRY", "")
    current_token = config.INSTAGRAM_API

    if not current_token:
        raise ValueError("INSTAGRAM_API token not set in .env")

    # Check if refresh is needed
    should_refresh = True
    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str.replace("'", ""))
            days_left = (expiry - datetime.now()).days
            logger.info("IG token expires in %d days (%s)", days_left, expiry_str)
            if days_left > 30:
                logger.info("IG token still fresh (%d days left) — skipping refresh", days_left)
                should_refresh = False
        except Exception as exc:
            logger.warning("Could not parse INSTAGRAM_TOKEN_EXPIRY: %s", exc)

    if not should_refresh:
        return {"ig_refreshed": False, "ig_days_left": days_left}

    # Call Meta to refresh
    logger.info("Refreshing Instagram long-lived token …")
    resp = requests.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": config.META_APP_ID,
            "client_secret": config.META_APP_SECRET,
            "fb_exchange_token": current_token,
        },
        timeout=30,
    )
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"Meta API error: {data['error'].get('message', data['error'])}")

    new_token = data.get("access_token")
    if not new_token:
        raise RuntimeError(f"No access_token in response: {data}")

    expires_in = data.get("expires_in", 5183944)  # default ~60 days
    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    new_expiry_str = new_expiry.isoformat()

    logger.info("✅ IG token refreshed. New expiry: %s", new_expiry_str)

    # Write back to .env
    _update_env("INSTAGRAM_API", new_token)
    _update_env("INSTAGRAM_TOKEN_EXPIRY", f"'{new_expiry_str}'")

    # Update in-memory config so current process uses new token
    os.environ["INSTAGRAM_API"] = new_token
    os.environ["INSTAGRAM_TOKEN_EXPIRY"] = new_expiry_str
    config.INSTAGRAM_API = new_token

    return {"ig_refreshed": True, "ig_new_expiry": new_expiry_str}


# ─────────────────────────────────────────────────────────────
# Facebook Page token
# ─────────────────────────────────────────────────────────────

def _fetch_facebook_page_token() -> dict:
    """
    Fetch the Facebook Page Access Token.
    If FACEBOOK_PAGE_NAME is set, finds that page by name from all accessible pages.
    Saves page ID + token to .env automatically.
    Page tokens derived from long-lived user tokens never expire.
    """
    user_token = config.INSTAGRAM_API
    target_name = os.getenv("FACEBOOK_PAGE_NAME", "").strip().lower()

    if not user_token:
        raise ValueError("INSTAGRAM_API token not set — cannot fetch FB page token")

    # Fetch ALL pages this token has access to (follow pagination)
    logger.info("Fetching all accessible Facebook Pages …")
    all_pages = []
    url = f"{GRAPH_BASE}/me/accounts"
    params = {"fields": "id,name,category,access_token", "limit": 100, "access_token": user_token}

    while url:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Meta API error fetching pages: {data['error'].get('message', data['error'])}")
        all_pages.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}  # next URL already has all params embedded

    if not all_pages:
        raise RuntimeError(
            "No Facebook Pages found for this token. "
            "Re-generate your token via Meta Graph Explorer and grant access to all your pages."
        )

    logger.info("Pages accessible with current token:")
    for p in all_pages:
        logger.info("  %-30s  ID: %s", p['name'], p['id'])

    # Find the target page by name
    chosen = None
    if target_name:
        for p in all_pages:
            if p["name"].lower() == target_name:
                chosen = p
                break
        if not chosen:
            # Try partial match
            for p in all_pages:
                if target_name in p["name"].lower():
                    chosen = p
                    break

    if not chosen:
        if target_name:
            names = ", ".join(p["name"] for p in all_pages)
            logger.warning(
                "Page '%s' not found among accessible pages: [%s]. "
                "Using first available page. Re-generate your token with all pages selected.",
                target_name, names
            )
        chosen = all_pages[0]

    page_token = chosen.get("access_token")
    page_id = chosen["id"]
    page_name = chosen["name"]

    if not page_token:
        raise RuntimeError(f"No access_token returned for page {page_name}")

    logger.info("✅ Using Facebook Page: '%s' (ID: %s)", page_name, page_id)

    # Persist page ID and token to .env + in-memory config
    _update_env("FACEBOOK_PAGE_ID", page_id)
    _update_env("FACEBOOK_PAGE_TOKEN", page_token)
    os.environ["FACEBOOK_PAGE_ID"] = page_id
    os.environ["FACEBOOK_PAGE_TOKEN"] = page_token
    config.FACEBOOK_PAGE_ID = page_id
    config.FACEBOOK_PAGE_TOKEN = page_token

    return {"fb_token_fetched": True, "fb_page_name": page_name, "fb_page_id": page_id}


# ─────────────────────────────────────────────────────────────
# Token status check (for /api/token-status)
# ─────────────────────────────────────────────────────────────

def get_token_status() -> dict:
    """Return current token health without making any API calls."""
    expiry_str = os.getenv("INSTAGRAM_TOKEN_EXPIRY", "")
    days_left = None
    status = "unknown"

    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str.strip("'"))
            days_left = (expiry - datetime.now()).days
            if days_left < 0:
                status = "expired"
            elif days_left < 7:
                status = "critical"
            elif days_left < 30:
                status = "expiring_soon"
            else:
                status = "ok"
        except Exception:
            status = "parse_error"

    fb_token_set = bool(os.getenv("FACEBOOK_PAGE_TOKEN", "").strip())

    return {
        "instagram_token": {
            "status": status,
            "days_left": days_left,
            "expiry": expiry_str,
        },
        "facebook_page_token": {
            "set": fb_token_set,
            "note": "Never expires when derived from long-lived user token",
        },
    }


# ─────────────────────────────────────────────────────────────
# .env writer (safe regex replacement)
# ─────────────────────────────────────────────────────────────

def _update_env(key: str, value: str) -> None:
    """
    Update or add a key=value line in .env without touching other lines.
    Thread-safe enough for a single-process app.
    """
    if not _ENV_PATH.exists():
        logger.warning(".env not found at %s — cannot persist token", _ENV_PATH)
        return

    content = _ENV_PATH.read_text(encoding="utf-8")
    pattern = rf"^{re.escape(key)}=.*$"
    new_line = f"{key}={value}"

    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
        logger.info("Updated %s in .env", key)
    else:
        content = content.rstrip("\n") + f"\n{new_line}\n"
        logger.info("Added %s to .env", key)

    _ENV_PATH.write_text(content, encoding="utf-8")
