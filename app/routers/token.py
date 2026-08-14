"""
routers/token.py
GET  /api/token-status    — show current token health (no API calls)
POST /api/refresh-token   — manually trigger token refresh immediately
"""
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tokens"])


@router.get("/token-status")
def token_status():
    """Show current token health without making any API calls."""
    from app.services.token_service import get_token_status
    return get_token_status()


@router.post("/refresh-token")
def refresh_token():
    """
    Manually trigger an immediate token refresh.
    - Refreshes IG long-lived token (if expiring within 30 days)
    - Fetches/updates Facebook Page Access Token
    - Writes new values to .env
    """
    from app.services.token_service import refresh_all_tokens
    try:
        result = refresh_all_tokens()
        if result.get("errors"):
            # Partial success — return 207
            return {"status": "partial", "details": result}
        return {"status": "ok", "details": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
