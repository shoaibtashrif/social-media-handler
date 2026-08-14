"""
routers/health.py — GET /health
Returns app status and scheduler job info.
"""
from fastapi import APIRouter
from app.services import scheduler_service

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    scheduler_info = scheduler_service.get_scheduler_info()
    return {
        "status": "ok",
        "scheduler": scheduler_info,
    }
