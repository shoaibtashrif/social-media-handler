from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
import json
from app.database import Base

class PostLog(Base):
    __tablename__ = "posts_log"

    id = Column(Integer, primary_key=True, index=True)
    post_type = Column(String, default="automated") # automated or manual
    reciter = Column(String, nullable=True)
    surah_name = Column(String, nullable=True)
    verses = Column(String, nullable=True)
    duration_s = Column(Float, nullable=True)
    video_file = Column(String, nullable=True)
    ig_post_id = Column(String, nullable=True)
    fb_post_id = Column(String, nullable=True)
    yt_post_id = Column(String, nullable=True)
    status = Column(String, default="success")
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Settings(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String) # Stored as JSON string

    def get_value(self):
        try:
            return json.loads(self.value)
        except:
            return self.value

    def set_value(self, val):
        self.value = json.dumps(val)
