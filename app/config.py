"""
config.py — Single source of truth for all .env settings.
When deploying to a new machine, only .env needs to change — never this file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file: app/ → project root)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def _get(key: str, default=None, required=False):
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


# ── Server ────────────────────────────────────────────────────
PORT: int = int(_get("PORT", 8009))
HOST: str = _get("HOST", "0.0.0.0")

# ── Tunnel (ngrok / Cloudflare) ───────────────────────────────
TUNNEL_URL: str = _get("TUNNEL_URL", "").rstrip("/")

# ── Meta / Instagram / Facebook ──────────────────────────────
INSTAGRAM_API: str = _get("INSTAGRAM_API", required=True)
INSTAGRAM_USER_ID: str = _get("INSTAGRAM_USER_ID", required=True)
FACEBOOK_PAGE_ID: str = _get("FACEBOOK_PAGE_ID", required=True)
META_APP_ID: str = _get("META_APP_ID", "")
META_APP_SECRET: str = _get("META_APP_SECRET", "")
# Page token — if blank, we'll try to use INSTAGRAM_API (user token).
# Note: posting to a Page requires a Page Access Token; set this if IG token doesn't work.
FACEBOOK_PAGE_TOKEN: str = _get("FACEBOOK_PAGE_TOKEN", "") or INSTAGRAM_API

# ── HuggingFace ───────────────────────────────────────────────
HF_TOKEN: str = _get("HF_TOKEN", "")

# ── Cloudflare (optional, not needed for core flow) ───────────
CF_API_TOKEN: str = _get("CF_API_TOKEN", "")
CF_ACCOUNT_ID: str = _get("CF_ACCOUNT_ID", "")

# ── Pollinations ──────────────────────────────────────────────
POLLINATIONS_API_KEY: str = _get("POLLINATIONS_API_KEY", "")

# ── Pexels ────────────────────────────────────────────────────
PEXELS_API_KEY: str = _get("PEXELS_API_KEY", "")

# ── Paths ─────────────────────────────────────────────────────
UPLOAD_MEDIA_DIR: Path = Path(_get("UPLOAD_MEDIA_DIR", "./upload_media")).resolve()
TEMP_DIR: Path = Path(_get("TEMP_DIR", "./junk")).resolve()
AUDIO_DIR: Path = TEMP_DIR / "audio"
VIDEO_DIR: Path = TEMP_DIR / "video"
LOG_DIR: Path = TEMP_DIR / "logs"
TRACKER_CSV: Path = LOG_DIR / "post_tracker.csv"
ROTATION_STATE: Path = LOG_DIR / "rotation_state.json"

# ── Scheduler ─────────────────────────────────────────────────
POSTS_PER_DAY: int = int(_get("POSTS_PER_DAY", 4))
POST_TIMES: list[str] = [t.strip() for t in _get("POST_TIMES", "09:00,12:30,16:30,21:00").split(",")]
TIMEZONE: str = _get("TIMEZONE", "Asia/Karachi")

# ── Qari config ───────────────────────────────────────────────
QARIS: list[dict] = [
    {"name": _get("QARI_1_NAME", "Ali Al-Hudhaify"),        "folder": _get("QARI_1_FOLDER", "Hudhaify_128kbps"), "is_youtube": False},
    {"name": _get("QARI_2_NAME", "Abdullah Basfar"),        "folder": _get("QARI_2_FOLDER", "Abdullah_Basfar_192kbps"), "is_youtube": False},
    {"name": _get("QARI_3_NAME", "Muhammad Ayyoub"),        "folder": _get("QARI_3_FOLDER", "Muhammad_Ayyoub_128kbps"), "is_youtube": False},
    {"name": "Othman Al Haddad",                            "folder": "youtube_othman", "is_youtube": True},
    {"name": "Abdur Rahman Mossad",                         "folder": "youtube_mossad", "is_youtube": True},
]

# ── Audio / Video ─────────────────────────────────────────────
MIN_DURATION: int = int(_get("MIN_DURATION", 40))
MAX_DURATION: int = int(_get("MAX_DURATION", 58))

# ── Verse pool — list of (surah, start_ayah, end_ayah) tuples ─
def _parse_verse_pool(raw: str) -> list[tuple[int, int, int]]:
    pool = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            surah_part, ayah_part = entry.split(":")
            if "-" in ayah_part:
                start, end = ayah_part.split("-")
            else:
                start = end = ayah_part
            pool.append((int(surah_part), int(start), int(end)))
        except Exception:
            pass
    return pool


_raw_pool = _get(
    "VERSE_POOL",
    "67:1-5,67:14-16,67:21-23,55:13-18,55:21-25,55:33-38,56:1-5,56:21-25,"
    "2:255-255,2:284-286,1:1-7,32:1-5,36:1-6,78:1-5",
)
VERSE_POOL: list[tuple[int, int, int]] = _parse_verse_pool(_raw_pool)

# ── Surah name map ────────────────────────────────────────────
SURAH_NAMES: dict[int, str] = {
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

# ── Ensure temp directories exist ─────────────────────────────
for _d in [AUDIO_DIR, VIDEO_DIR, LOG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
