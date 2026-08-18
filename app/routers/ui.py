from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List

from app.database import SessionLocal
from app.models import PostLog
from app import config
from app.services import settings_service, scheduler_service, log_service

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="app/templates")

class ScheduleItem(BaseModel):
    time: str
    qari: str

class SettingsPayload(BaseModel):
    schedule: List[ScheduleItem]
    auto_upload: bool = True

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = SessionLocal()
    try:
        posts = db.query(PostLog).order_by(PostLog.created_at.desc()).limit(20).all()
    finally:
        db.close()
    
    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={"request": request, "posts": posts}
    )

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="upload.html", context={"request": request}
    )

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    current_settings = settings_service.get_all_settings()
    qaris = config.QARIS
    return templates.TemplateResponse(
        request=request, name="settings.html", context={
            "request": request,
            "settings": current_settings,
            "qaris": qaris
        }
    )

@router.post("/ui/settings")
async def save_settings(payload: SettingsPayload):
    settings_service.set_setting("schedule", [item.dict() for item in payload.schedule])
    settings_service.set_setting("auto_upload", payload.auto_upload)
    
    # Reload APScheduler with new settings
    scheduler_service.reload_scheduler()
    
    return {"status": "success", "message": "Settings updated"}

@router.get("/api/notifications")
async def get_notifications():
    db = SessionLocal()
    try:
        count = db.query(PostLog).count()
        latest = db.query(PostLog).order_by(PostLog.created_at.desc()).first()
        if latest:
            return {
                "latest_count": count,
                "latest_post": {
                    "status": latest.status,
                    "video_file": latest.video_file,
                    "notes": latest.notes
                }
            }
        return {"latest_count": 0, "latest_post": None}
    finally:
        db.close()

@router.get("/api/logs/stream")
async def stream_logs():
    return StreamingResponse(log_service.log_streamer(), media_type="text/event-stream")

@router.get("/server-logs")
async def server_logs():
    import os
    from fastapi.responses import PlainTextResponse
    log_path = "main.log"
    if not os.path.exists(log_path):
        return PlainTextResponse("No logs available yet. Ensure server is started with nohup.", status_code=404)
    with open(log_path, "r") as f:
        content = f.read()
    return PlainTextResponse(content)
