from app.database import SessionLocal
from app.models import Settings
import json

DEFAULT_SETTINGS = {
    "schedule": [
        {"time": "09:00", "qari": "random"},
        {"time": "12:30", "qari": "random"},
        {"time": "16:30", "qari": "random"},
        {"time": "21:00", "qari": "random"}
    ]
}

def get_setting(key: str, default=None):
    db = SessionLocal()
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting:
            return setting.get_value()
        
        # Fallback to defaults
        if key in DEFAULT_SETTINGS:
            # Initialize it
            set_setting(key, DEFAULT_SETTINGS[key])
            return DEFAULT_SETTINGS[key]
        return default
    finally:
        db.close()

def set_setting(key: str, value):
    db = SessionLocal()
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()
        if not setting:
            setting = Settings(key=key)
            db.add(setting)
        setting.set_value(value)
        db.commit()
    finally:
        db.close()

def get_all_settings():
    db = SessionLocal()
    try:
        settings_rows = db.query(Settings).all()
        current = {row.key: row.get_value() for row in settings_rows}
        
        # Ensure defaults are merged if not exists
        for k, v in DEFAULT_SETTINGS.items():
            if k not in current:
                set_setting(k, v)
                current[k] = v
        return current
    finally:
        db.close()
