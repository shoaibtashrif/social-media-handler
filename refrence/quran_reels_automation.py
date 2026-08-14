Automated Quran Reels Poster
Posts every hour with:
- 3 Qaris rotation: Othman Al-Haddad, Abdul Rehman Masood, Mishary Rashid
- Precise verse-by-verse audio from EveryAyah/Archive.org
- No Bismillah, not from beginning, complete verse ranges
- Random duration 30s-1m45s
- User-uploaded sunset/sunrise backgrounds
- No text on image — pure image + voiceover
- Posts to Facebook & Instagram via Flask API
"""

import os
import sys
import json
import csv
import random
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# === CONFIG ===
FLASK_URL = "http://127.0.0.1:8009"
TUNNEL_URL = "https://pencil-dublin-hopefully-persistent.trycloudflare.com"
TRACK_FILE = "/home/ubuntu/quran_reels_tracker.csv"
AUDIO_DIR = "/tmp/quran_audio_clips"
VIDEO_DIR = "/tmp/quran_videos"
SUNSET_DIR = "/home/ubuntu/quran_sunset_images"  # USER UPLOADED IMAGES
LOG_FILE = "/home/ubuntu/quran_reels.log"

ROTATION_STATE_FILE = "/home/ubuntu/quran_rotation_state.json"

# === QARI AUDIO LIBRARIES (Precise EveryAyah/Archive.org verse concatenation) ===
QARI_LIBRARIES = {
    "Othman_Al_Haddad": {
        "reciter": "Othman Al-Haddad (عثمان مشعل الحدادي)",
        "style": "Deep, powerful, Meccan style",
        "source": "archive_org",
        "clips": [
            {"surah": 1, "start": 1, "end": 7, "duration": 49, "file": "/tmp/clip_othman_othman_fatiha.mp3"},
            {"surah": 32, "start": 1, "end": 30, "duration": 75, "file": "/tmp/clip_othman_othman_sajdah.mp3"},
            {"surah": 55, "start": 18, "end": 11, "duration": 162, "file": "/tmp/clip_othman_othman_rahman_viral.mp3"},
            {"surah": 67, "start": 40, "end": 50, "duration": 125, "file": "/tmp/clip_othman_othman_mulk_aya40_50.mp3"},
            {"surah": 56, "start": 1, "end": 14, "duration": 90, "file": "/tmp/clip_othman_othman_waqiah.mp3"},
        ]
    },
    "Abdul_Rehman_Masood": {
        "reciter": "Abdul Rehman Masood (عبد الرحمن مسعد)",
        "style": "Egyptian, melodious, clear tajweed",
        "source": "archive_org",
        "clips": [
            {"surah": 1, "start": 1, "end": 7, "duration": 49, "file": "/tmp/abdul_masood/001 Al-Fatiha %D8%A7%D9%84%D9%81%D8%A7%D8%AA%D8%AD%D8%A9.mp3"},
            {"surah": 2, "start": 197, "end": 202, "duration": 185, "file": "/tmp/abdul_masood/002 Al-Baqara 197-202 %D8%A7%D9%84%D8%A8%D9%82%D8%B1%D8%A9.mp3"},
            {"surah": 2, "start": 44, "end": 46, "duration": 60, "file": "/tmp/abdul_masood/002 Al-Baqara 44-46 %D8%A7%D9%84%D8%A8%D9%82%D8%B1%D8%A9.mp3"},
            {"surah": 7, "start": 196, "end": 206, "duration": 210, "file": "/tmp/abdul_masood/007 Al-A%27raf 196-206 %D8%A7%D9%84%D8%A3%D8%B9%D8%B1%D8%A7%D9%81.mp3"},
            {"surah": 10, "start": 3, "end": 25, "duration": 867, "file": "/tmp/abdul_masood/010 Yunus 3-25 %D9%8A%D9%88%D9%86%D8%B3.mp3"},
            {"surah": 12, "start": 102, "end": 111, "duration": 251, "file": "/tmp/abdul_masood/012 Yusuf 102-111 %D9%8A%D9%88%D8%B3%D9%81.mp3"},
            {"surah": 16, "start": 52, "end": 64, "duration": 255, "file": "/tmp/abdul_masood/016 An-Nahl 52-64 %D8%A7%D9%86%D8%AD%D9%84.mp3"},
            {"surah": 16, "start": 90, "end": 99, "duration": 288, "file": "/tmp/abdul_masood/016 An-Nahl 90-99 %D8%A7%D9%86%D8%AD%D9%84.mp3"},
        ]
    },
    "Mishary_Rashid": {
        "reciter": "Mishary Rashid Alafasy (مشاري راشد العفاسي)",
        "style": "Emotional, modern, very popular",
        "source": "everyayah",
        "clips": [
            {"surah": 2, "start": 255, "end": 255, "duration": 52, "file": "/tmp/precise_Alafasy_128kbps_2_255_255.mp3"},
            {"surah": 2, "start": 284, "end": 286, "duration": 117, "file": "/tmp/precise_Alafasy_128kbps_2_284_286.mp3"},
            {"surah": 55, "start": 13, "end": 18, "duration": 119, "file": "/tmp/precise_Alafasy_128kbps_55_13_18.mp3"},
            {"surah": 55, "start": 21, "end": 25, "duration": 115, "file": "/tmp/precise_Alafasy_128kbps_55_21_25.mp3"},
            {"surah": 67, "start": 1, "end": 5, "duration": 26, "file": "/tmp/precise_Alafasy_128kbps_67_1_5.mp3"},
            {"surah": 55, "start": 1, "end": 5, "duration": 58, "file": "/tmp/precise_Alafasy_128kbps_55_1_5.mp3"},
            {"surah": 55, "start": 33, "end": 38, "duration": 80, "file": "/tmp/precise_Alafasy_128kbps_55_33_38.mp3"},
            {"surah": 56, "start": 21, "end": 25, "duration": 123, "file": "/tmp/precise_Alafasy_128kbps_56_21_25.mp3"},
            {"surah": 67, "start": 14, "end": 16, "duration": 30, "file": "/tmp/precise_Alafasy_128kbps_67_14_16.mp3"},
            {"surah": 67, "start": 21, "end": 23, "duration": 25, "file": "/tmp/precise_Alafasy_128kbps_67_21_23.mp3"},
            {"surah": 56, "start": 1, "end": 5, "duration": 30, "file": "/tmp/precise_Alafasy_128kbps_56_1_5.mp3"},
        ]
    },
}

# QARI ROTATION ORDER
QARI_ROTATION = ["Othman_Al_Haddad", "Abdul_Rehman_Masood", "Mishary_Rashid"]

# Duration ranges (seconds)
DURATION_RANGES = [
    (30, 45),   # 30-45s
    (45, 60),   # 45-60s
    (60, 90),   # 1-1.5 min
    (90, 105),  # 1.5-1.75 min
]

# Surah names
SURAH_NAMES = {
    1: "Al-Fatiha", 2: "Al-Baqarah", 3: "Al-Imran", 4: "An-Nisa",
    5: "Al-Ma'idah", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
    9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
    13: "Ar-Ra'd", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
    17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Taha",
    21: "Al-Anbiya", 22: "Al-Hajj", 23: "Al-Mu'minun", 24: "An-Nur",
    25: "Al-Furqan", 26: "Ash-Shu'ara", 27: "An-Naml", 28: "Al-Qasas",
    29: "Al-Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah",
    33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya-Sin",
    37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
    41: "Fussilat", 42: "Ash-Shura", 44: "Ad-Dukhan", 45: "Al-Jathiyah",
    46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath", 49: "Al-Hujurat",
    50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur", 53: "An-Najm",
    54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqiah", 57: "Al-Hadid",
    58: "Al-Mujadilah", 59: "Al-Hashr", 60: "Al-Mumtahanah",
    61: "As-Saff", 62: "Al-Jumu'ah", 63: "Al-Munafiqun", 64: "At-Taghabun",
    65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
    69: "Al-Haqqah", 70: "Al-Ma'arij", 71: "Nuh", 72: "Al-Jinn",
    73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah",
    76: "Al-Insan", 77: "Al-Mursalat", 78: "An-Naba", 79: "An-Nazi'at",
    80: "Abasa", 81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin",
    84: "Al-Inshiqaq", 85: "Al-Buruj", 86: "At-Tariq", 87: "Al-A'la",
    88: "Al-Ghashiyah", 89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams",
    92: "Al-Layl", 93: "Ad-Duha", 95: "At-Tin", 96: "Al-Alaq",
    97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Al-Zalzalah", 100: "Al-Adiyat",
    101: "Al-Qari'ah", 102: "At-Takathur", 103: "Al-Asr", 104: "Al-Humazah",
    105: "Al-Fil", 106: "Quraysh", 107: "Al-Ma'un", 108: "Al-Kawthar",
    109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
    113: "Al-Falaq", 114: "An-Nas",
}

# Duration ranges (seconds)
DURATION_RANGES = [
    (30, 45),   # 30-45s
    (45, 60),   # 45-60s
    (60, 90),   # 1-1.5 min
    (90, 105),  # 1.5-1.75 min
]

# QARI ROTATION ORDER
QARI_ROTATION = ["Othman_Al_Haddad", "Abdul_Rehman_Masood", "Mishary_Rashid"]

# === SETUP ===
FLASK_URL = "http://127.0.0.1:8009"
TUNNEL_URL = "https://pencil-dublin-hopefully-persistent.trycloudflare.com"
TRACK_FILE = "/home/ubuntu/quran_reels_tracker.csv"
AUDIO_DIR = "/tmp/quran_audio_clips"
VIDEO_DIR = "/tmp/quran_videos"
SUNSET_DIR = "/home/ubuntu/quran_sunset_images"
LOG_FILE = "/home/ubuntu/quran_reels.log"

ROTATION_STATE_FILE = "/home/ubuntu/quran_rotation_state.json"

# === QARI AUDIO LIBRARIES ===
QARI_LIBRARIES = {
    "Othman_Al_Haddad": {
        "reciter": "Othman Al-Haddad (عثمان مشعل الحدادي)",
        "style": "Deep, powerful, Meccan style",
        "source": "archive_org",
        "clips": [
            {"surah": 1, "start": 1, "end": 7, "duration": 49, "file": "/tmp/clip_othman_othman_fatiha.mp3"},
            {"surah": 32, "start": 1, "end": 30, "duration": 75, "file": "/tmp/clip_othman_othman_sajdah.mp3"},
            {"surah": 55, "start": 18, "end": 11, "duration": 162, "file": "/tmp/clip_othman_othman_rahman_viral.mp3"},
            {"surah": 67, "start": 40, "end": 50, "duration": 125, "file": "/tmp/clip_othman_othman_mulk_aya40_50.mp3"},
            {"surah": 56, "start": 1, "end": 14, "duration": 90, "file": "/tmp/clip_othman_othman_waqiah.mp3"},
        ]
    },
    "Abdul_Rehman_Masood": {
        "reciter": "Abdul Rehman Masood (عبد الرحمن مسعد)",
        "style": "Egyptian, melodious, clear tajweed",
        "source": "archive_org",
        "clips": [
            {"surah": 1, "start": 1, "end": 7, "duration": 49, "file": "/tmp/abdul_masood/001 Al-Fatiha %D8%A7%D9%84%D9%81%D8%A7%D8%AA%D8%AD%D8%A9.mp3"},
            {"surah": 2, "start": 197, "end": 202, "duration": 185, "file": "/tmp/abdul_masood/002 Al-Baqara 197-202 %D8%A7%D9%84%D8%A8%D9%82%D8%B1%D8%A9.mp3"},
            {"surah": 2, "start": 44, "end": 46, "duration": 60, "file": "/tmp/abdul_masood/002 Al-Baqara 44-46 %D8%A7%D9%84%D8%A8%D9%82%D8%B1%D8%A9.mp3"},
            {"surah": 7, "start": 196, "end": 206, "duration": 210, "file": "/tmp/abdul_masood/007 Al-A%27raf 196-206 %D8%A7%D9%84%D8%A3%D8%B9%D8%B1%D8%A7%D9%81.mp3"},
            {"surah": 10, "start": 3, "end": 25, "duration": 867, "file": "/tmp/abdul_masood/010 Yunus 3-25 %D9%8A%D9%88%D9%86%D8%B3.mp3"},
            {"surah": 12, "start": 102, "end": 111, "duration": 251, "file": "/tmp/abdul_masood/012 Yusuf 102-111 %D9%8A%D9%88%D8%B3%D9%81.mp3"},
            {"surah": 16, "start": 52, "end": 64, "duration": 255, "file": "/tmp/abdul_masood/016 An-Nahl 52-64 %D8%A7%D9%86%D8%AD%D9%84.mp3"},
            {"surah": 16, "start": 90, "end": 99, "duration": 288, "file": "/tmp/abdul_masood/016 An-Nahl 90-99 %D8%A7%D9%86%D8%AD%D9%84.mp3"},
        ]
    },
    "Mishary_Rashid": {
        "reciter": "Mishary Rashid Alafasy (مشاري راشد العفاسي)",
        "style": "Emotional, modern, very popular",
        "source": "everyayah",
        "clips": [
            {"surah": 2, "start": 255, "end": 255, "duration": 52, "file": "/tmp/precise_Alafasy_128kbps_2_255_255.mp3"},
            {"surah": 2, "start": 284, "end": 286, "duration": 117, "file": "/tmp/precise_Alafasy_128kbps_2_284_286.mp3"},
            {"surah": 55, "start": 13, "end": 18, "duration": 119, "file": "/tmp/precise_Alafasy_128kbps_55_13_18.mp3"},
            {"surah": 55, "start": 21, "end": 25, "duration": 115, "file": "/tmp/precise_Alafasy_128kbps_55_21_25.mp3"},
            {"surah": 67, "start": 1, "end": 5, "duration": 26, "file": "/tmp/precise_Alafasy_128kbps_67_1_5.mp3"},
            {"surah": 55, "start": 1, "end": 5, "duration": 58, "file": "/tmp/precise_Alafasy_128kbps_55_1_5.mp3"},
            {"surah": 55, "start": 33, "end": 38, "duration": 80, "file": "/tmp/precise_Alafasy_128kbps_55_33_38.mp3"},
            {"surah": 56, "start": 21, "end": 25, "duration": 123, "file": "/tmp/precise_Alafasy_128kbps_56_21_25.mp3"},
            {"surah": 67, "start": 14, "end": 16, "duration": 30, "file": "/tmp/precise_Alafasy_128kbps_67_14_16.mp3"},
            {"surah": 67, "start": 21, "end": 23, "duration": 25, "file": "/tmp/precise_Alafasy_128kbps_67_21_23.mp3"},
            {"surah": 56, "start": 1, "end": 5, "duration": 30, "file": "/tmp/precise_Alafasy_128kbps_56_1_5.mp3"},
        ]
    },
}

# QARI ROTATION ORDER
QARI_ROTATION = ["Othman_Al_Haddad", "Abdul_Rehman_Masood", "Mishary_Rashid"]

# Duration ranges (seconds)
DURATION_RANGES = [
    (30, 45),   # 30-45s
    (45, 60),   # 45-60s
    (60, 90),   # 1-1.5 min
    (90, 105),  # 1.5-1.75 min
]

# Surah names
SURAH_NAMES = {
    1: "Al-Fatiha", 2: "Al-Baqarah", 3: "Al-Imran", 4: "An-Nisa",
    5: "Al-Ma'idah", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
    9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
    13: "Ar-Ra'd", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
    17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Taha",
    21: "Al-Anbiya", 22: "Al-Hajj", 23: "Al-Mu'minun", 24: "An-Nur",
    25: "Al-Furqan", 26: "Ash-Shu'ara", 27: "An-Naml", 28: "Al-Qasas",
    29: "Al-Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah",
    33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya-Sin",
    37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
    41: "Fussilat", 42: "Ash-Shura", 44: "Ad-Dukhan", 45: "Al-Jathiyah",
    46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath", 49: "Al-Hujurat",
    50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur", 53: "An-Najm",
    54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqiah", 57: "Al-Hadid",
    58: "Al-Mujadilah", 59: "Al-Hashr", 60: "Al-Mumtahanah",
    61: "As-Saff", 62: "Al-Jumu'ah", 63: "Al-Munafiqun", 64: "At-Taghabun",
    65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
    69: "Al-Haqqah", 70: "Al-Ma'arij", 71: "Nuh", 72: "Al-Jinn",
    73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah",
    76: "Al-Insan", 77: "Al-Mursalat", 78: "An-Naba", 79: "An-Nazi'at",
    80: "Abasa", 81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin",
    84: "Al-Inshiqaq", 85: "Al-Buruj", 86: "At-Tariq", 87: "Al-A'la",
    88: "Al-Ghashiyah", 89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams",
    92: "Al-Layl", 93: "Ad-Duha", 95: "At-Tin", 96: "Al-Alaq",
    97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Al-Zalzalah", 100: "Al-Adiyat",
    101: "Al-Qari'ah", 102: "At-Takathur", 103: "Al-Asr", 104: "Al-Humazah",
    105: "Al-Fil", 106: "Quraysh", 107: "Al-Ma'un", 108: "Al-Kawthar",
    109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
    113: "Al-Falaq", 114: "An-Nas",
}

# Duration ranges (seconds)
DURATION_RANGES = [
    (30, 45),   # 30-45s
    (45, 60),   # 45-60s
    (60, 90),   # 1-1.5 min
    (90, 105),  # 1.5-1.75 min
]

# QARI ROTATION ORDER
QARI_ROTATION = ["Othman_Al_Haddad", "Abdul_Rehman_Masood", "Mishary_Rashid"]

# === SETUP ===
FLASK_URL = "http://127.0.0.1:8009"
TUNNEL_URL = "https://pencil-dublin-hopefully-persistent.trycloudflare.com"
TRACK_FILE = "/home/ubuntu/quran_reels_tracker.csv"
AUDIO_DIR = "/tmp/quran_audio_clips"
VIDEO_DIR = "/tmp/quran_videos"
SUNSET_DIR = "/home/ubuntu/quran_sunset_images"
LOG_FILE = "/home/ubuntu/quran_reels.log"

ROTATION_STATE_FILE = "/home/ubuntu/quran_rotation_state.json"

# === SETUP ===
def setup_dirs():
    for d in [AUDIO_DIR, VIDEO_DIR, SUNSET_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)

def init_tracker():
    if not Path(TRACK_FILE).exists():
        with open(TRACK_FILE, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow([
                "date", "time", "reciter", "surah", "start_ayah", "end_ayah",
                "duration", "video_file", "video_url", "fb_post_id", "ig_post_id",
                "status", "notes"
            ])

def load_rotation_state():
    if Path(ROTATION_STATE_FILE).exists():
        with open(ROTATION_STATE_FILE, 'r') as f:
            return json.load(f)
    return {"next_qari_index": 0}

def save_rotation_state(state):
    with open(ROTATION_STATE_FILE, 'w') as f:
        json.dump(state, f)

def get_next_qari():
    state = load_rotation_state()
    idx = state.get("next_qari_index", 0)
    qari = QARI_ROTATION[idx]
    state["next_qari_index"] = (idx + 1) % len(QARI_ROTATION)
    save_rotation_state(state)
    return qari

def log_entry(entry):
    with open(TRACK_FILE, 'a', newline='') as f:
        w = csv.writer(f)
        w.writerow(entry)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(full_msg + "\n")

# === AUDIO PROCESSING ===
def trim_audio(input_file, output_file, target_duration):
    """Trim or loop audio to target duration"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", input_file
    ], capture_output=True, text=True)
    
    duration_str = result.stdout.strip()
    if not duration_str:
        raise ValueError(f"Could not get duration for {input_file}")
    
    actual_duration = float(duration_str)
    log(f"Audio: {input_file} duration={actual_duration:.2f}s, target={target_duration}s")
    
    if actual_duration >= target_duration:
        result = subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-ss", "0", "-t", str(target_duration),
            "-c:a", "copy", output_file
        ], capture_output=True, text=True)
        if result.returncode != 0:
            log(f"FFmpeg trim error: {result.stderr}")
            raise RuntimeError(f"FFmpeg trim failed: {result.stderr}")
    else:
        loops = int(target_duration / actual_duration) + 1
        concat_file = "/tmp/concat_list.txt"
        with open(concat_file, "w") as f:
            for _ in range(loops):
                f.write(f"file '{input_file}'\n")
        
        result = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", "/tmp/concat_list.txt",
            "-t", str(target_duration),
            "-c:a", "aac", "-b:a", "192k", output_file
        ], capture_output=True, text=True)
        if result.returncode != 0:
            log(f"FFmpeg concat error: {result.stderr}")
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")

def prepare_audio_clip(reciter_name, clip_info, target_duration):
    """Prepare audio clip with target duration"""
    input_file = clip_info["file"]
    output_file = os.path.join(AUDIO_DIR, f"{reciter_name}_surah{clip_info['surah']}_{clip_info['start']}_{clip_info['end']}_{target_duration}s.mp3")
    
    if not os.path.exists(input_file):
        log(f"Input file missing: {input_file}")
        import glob
        pattern = os.path.join(os.path.dirname(input_file), "*.mp3")
        files = glob.glob(pattern)
        if files:
            input_file = files[0]
            log(f"Using alternative: {input_file}")
        else:
            log(f"No audio files found in {os.path.dirname(input_file)}")
            os.makedirs(AUDIO_DIR, exist_ok=True)
            output_file = os.path.join(AUDIO_DIR, f"{reciter_name}_silence_{target_duration}s.mp3")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(target_duration), "-c:a", "aac", "-b:a", "192k", output_file
            ], capture_output=True)
            return output_file, target_duration
    
    try:
        trim_audio(input_file, output_file, target_duration)
        log(f"Audio prepared: {output_file}")
    except Exception as e:
        log(f"Audio trim error: {e}")
        import shutil
        shutil.copy2(input_file, output_file)
    
    if not os.path.exists(output_file):
        log(f"Output file missing: {output_file}")
        return input_file, target_duration
    
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", output_file
        ], capture_output=True, text=True)
        
        duration_str = result.stdout.strip()
        if not duration_str:
            raise ValueError(f"Could not get duration for {output_file}")
        actual = float(duration_str)
        log(f"Audio ready: {output_file} ({actual:.1f}s)")
    except Exception as e:
        log(f"Duration check error: {e}")
        actual = target_duration
    
    return output_file, actual

# === VIDEO CREATION ===
def create_video(audio_file, image_file, output_file):
    """Create video from image + audio"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    result = subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_file,
        "-i", audio_file,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest", output_file
    ], capture_output=True, text=True)
    if result.returncode != 0:
        log(f"Video creation error: {result.stderr}")
        raise RuntimeError(f"Video creation failed: {result.stderr}")
    log(f"Video created: {output_file}")

# === UPLOAD & POST ===
def upload_video(video_file):
    try:
        with open(video_file, 'rb') as f:
            files = {"file": (os.path.basename(video_file), f, "video/mp4")}
            r = requests.post(f"{FLASK_URL}/api/upload-media", files=files, timeout=60)
        if r.status_code == 200:
            data = r.json()
            return data.get("url")
    except Exception as e:
        log(f"Upload error: {e}")
    return None

def post_video(video_url, caption):
    try:
        payload = {
            "video_url": video_url,
            "caption": caption,
            "platform": "both",
            "media_type": "video"
        }
        r = requests.post(f"{FLASK_URL}/api/post-now", json=payload, timeout=120)
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                return data.get("fb_post_id"), data.get("ig_post_id")
    except Exception as e:
        log(f"Post error: {e}")
    return None, None

# === MAIN POSTING FUNCTION ===
def create_and_post():
    try:
        # 1. Get next Qari in rotation
        qari_name = get_next_qari()
        reciter_info = QARI_LIBRARIES[qari_name]
        
        # 2. Select random clip from that Qari's library
        clip = random.choice(reciter_info["clips"])
        
        # 3. Select random duration
        dur_range = random.choice(DURATION_RANGES)
        target_duration = random.randint(dur_range[0], dur_range[1])
        
        # 3. Prepare audio
        audio_file, actual_dur = prepare_audio_clip(qari_name, clip, target_duration)
        
        # 4. Select random user-uploaded sunset/sunrise image
        sunset_files = list(Path(SUNSET_DIR).glob("*.jpeg")) + list(Path(SUNSET_DIR).glob("*.jpg")) + list(Path(SUNSET_DIR).glob("*.png"))
        if not sunset_files:
            log("No sunset images found!")
            return False
        image_file = str(random.choice(sunset_files))
        
        # 5. Create video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = f"{qari_name}_surah{clip['surah']}_{clip['start']}_{clip['end']}_{timestamp}.mp4"
        video_file = os.path.join(VIDEO_DIR, video_name)
        
        create_video(audio_file, image_file, video_file)
        
        # 6. Upload
        local_url = upload_video(video_file)
        if not local_url:
            log("Failed to upload video")
            return False
        
        video_url = f"{TUNNEL_URL}{local_url}"
        
        # 7. Generate caption
        surah_name = SURAH_NAMES.get(clip['surah'], f"Surah {clip['surah']}")
        
        caption = f"""🌅 {surah_name} ({clip['surah']}:{clip['start']}-{clip['end']})

🎙️ Reciter: {QARI_LIBRARIES[qari_name]['reciter']}
🎨 Style: {QARI_LIBRARIES[qari_name]['style']}
🌅 Sunset/Sunrise background

#Quran #QuranRecitation #{surah_name.replace(' ', '')} #Surah{clip['surah']} #QuranVerses
#QuranReels #IslamicVideo #SpiritualContent"""
        
        # 7. Post
        fb_id, ig_id = post_video(f"{TUNNEL_URL}{local_url}", caption)
        
        # 8. Log
        log_entry([
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            QARI_LIBRARIES[qari_name]['reciter'],
            clip['surah'], clip['start'], clip['end'],
            actual_dur, video_name, video_url,
            fb_id or "failed", ig_id or "failed",
            "success" if fb_id else "failed",
            f"Duration: {actual_dur}s"
        ])
        
        log(f"✅ Posted: {QARI_LIBRARIES[qari_name]['reciter']} - {surah_name} {clip['start']}-{clip['end']} ({actual_dur}s)")
        return True
        
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        log(traceback.format_exc())
        log_entry([
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            "ERROR", "", "", "", "", "", "", "", "",
            "error", str(e)
        ])
        return False

# === SETUP ===
def setup_dirs():
    for d in [AUDIO_DIR, VIDEO_DIR, SUNSET_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)

def init_tracker():
    if not Path(TRACK_FILE).exists():
        with open(TRACK_FILE, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow([
                "date", "time", "reciter", "surah", "start_ayah", "end_ayah",
                "duration", "video_file", "video_url", "fb_post_id", "ig_post_id",
                "status", "notes"
            ])

def init_rotation_state():
    if not Path(ROTATION_STATE_FILE).exists():
        save_rotation_state({"next_qari_index": 0})

def log_entry(entry):
    with open(TRACK_FILE, 'a', newline='') as f:
        w = csv.writer(f)
        w.writerow(entry)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(full_msg + "\n")

# === MAIN ===
def create_and_post():
    try:
        # 1. Get next Qari in rotation
        qari_name = get_next_qari()
        reciter_info = QARI_LIBRARIES[qari_name]
        
        # 2. Select random clip from that Qari's library
        clip = random.choice(reciter_info["clips"])
        
        # 3. Select random duration
        dur_range = random.choice(DURATION_RANGES)
        target_duration = random.randint(dur_range[0], dur_range[1])
        
        # 4. Prepare audio
        audio_file, actual_dur = prepare_audio_clip(qari_name, clip, target_duration)
        
        # 5. Select random user-uploaded sunset/sunrise image
        sunset_files = list(Path(SUNSET_DIR).glob("*.jpeg")) + list(Path(SUNSET_DIR).glob("*.jpg")) + list(Path(SUNSET_DIR).glob("*.png"))
        if not sunset_files:
            log("No sunset images found!")
            return False
        image_file = str(random.choice(sunset_files))
        
        # 6. Create video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = f"{qari_name}_surah{clip['surah']}_{clip['start']}_{clip['end']}_{timestamp}.mp4"
        video_file = os.path.join(VIDEO_DIR, video_name)
        
        create_video(audio_file, image_file, video_file)
        
        # 7. Upload
        local_url = upload_video(video_file)
        if not local_url:
            log("Failed to upload video")
            return False
        
        video_url = f"{TUNNEL_URL}{local_url}"
        
        # 8. Generate caption
        surah_name = SURAH_NAMES.get(clip['surah'], f"Surah {clip['surah']}")
        
        caption = f"""🌅 {surah_name} ({clip['surah']}:{clip['start']}-{clip['end']})

🎙️ Reciter: {QARI_LIBRARIES[qari_name]['reciter']}
🎨 Style: {QARI_LIBRARIES[qari_name]['style']}
🌅 Sunset/Sunrise background

#Quran #QuranRecitation #{surah_name.replace(' ', '')} #Surah{clip['surah']} #QuranVerses
#QuranReels #IslamicVideo #SpiritualContent"""
        
        # 9. Post
        fb_id, ig_id = post_video(f"{TUNNEL_URL}{local_url}", caption)
        
        # 10. Log
        log_entry([
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            QARI_LIBRARIES[qari_name]['reciter'],
            clip['surah'], clip['start'], clip['end'],
            actual_dur, video_name, video_url,
            fb_id or "failed", ig_id or "failed",
            "success" if fb_id else "failed",
            f"Duration: {actual_dur}s"
        ])
        
        log(f"✅ Posted: {QARI_LIBRARIES[qari_name]['reciter']} - {surah_name} {clip['start']}-{clip['end']} ({actual_dur}s)")
        return True
        
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        log(traceback.format_exc())
        log_entry([
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            "ERROR", "", "", "", "", "", "", "", "",
            "error", str(e)
        ])
        return False

if __name__ == "__main__":
    import csv
    import requests
    import subprocess
    from pathlib import Path
    from datetime import datetime
    
    setup_dirs()
    init_tracker()
    init_rotation_state()
    log("=== Quran Reels Poster Started ===")
    
    success = create_and_post()
