# Quran Automator

A complete automated social media bot that generates and posts high-quality, copyright-free Quran recitation videos to Instagram, Facebook, and YouTube Shorts. 

The bot automatically downloads beautiful 9:16 (Reel format) nature background clips, concatenates them, overlays heavy or minor edited Quran recitations (to bypass copyright bots), applies aesthetic filters, and schedules posts multiple times a day.

---

## Features

- **Multi-Platform Posting:** Simultaneously posts to Instagram Reels, Facebook Reels, and YouTube Shorts.
- **Dynamic Backgrounds:** Automatically fetches copyright-free nature/aesthetic clips from YouTube and concatenates them for a dynamic visual experience.
- **Copyright Bypass Audio:** Configurable audio editing modes (Heavy, Minor, Original) to add slowed reverb, pitch shifts, and soft background rain to avoid automated copyright claims.
- **Web Dashboard:** A local web UI to monitor live logs, view posting history, trigger manual posts, and configure the automated scheduler.
- **Archive.org Integration:** Directly streams recitations from Archive.org to bypass YouTube's strict anti-bot measures.

---

## Prerequisites

Before running the application, ensure you have the following installed on your system:

1. **Python 3.10+**: `python3 --version`
2. **FFmpeg**: Required for audio/video processing.
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```
3. **yt-dlp**: Required for downloading background videos.
   ```bash
   sudo wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp
   sudo chmod a+rx /usr/local/bin/yt-dlp
   ```

---

## Step-by-Step Setup Guide

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd social-media-handler
```

### 2. Install Python Dependencies
It is highly recommended to use a virtual environment.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables
Copy the `.env.example` file (if available) or create a new `.env` file in the root directory. You must fill in your API keys:

```env
# Server
PORT=8009
HOST=0.0.0.0

# Tunnel (e.g., ngrok or Cloudflare tunnel URL to your localhost)
TUNNEL_URL=https://your-tunnel-url.ngrok-free.app

# Meta (Instagram & Facebook)
INSTAGRAM_API=your_instagram_user_access_token
INSTAGRAM_USER_ID=your_instagram_account_id
FACEBOOK_PAGE_ID=your_facebook_page_id
FACEBOOK_PAGE_TOKEN=your_facebook_page_access_token

# Application Settings
TIMEZONE=Asia/Karachi
```

> **Note:** The `TUNNEL_URL` is critically important for Meta. Instagram/Facebook requires a public URL to download the generated `.mp4` file.

### 4. Setting up YouTube (Optional but recommended)
To post to YouTube Shorts, you must place your Google OAuth `client_secrets.json` file in the root directory. The application will guide you through the OAuth flow the first time it tries to post to YouTube, and will generate a `youtube_token.json` file.

### 5. Add Fallback Media
In case the internet is down or the YouTube scraper fails, the script will fall back to local media. 
Add a few `.mp4` or `.jpg` files inside the `upload_media/` directory.

### 6. Run the Application
Start the server and background scheduler:
```bash
python3 run.py
```

Open your browser and navigate to:
**http://localhost:8009**

---

## Using the Dashboard

1. **Dashboard:** View the status of recent posts and read live server logs.
2. **Settings:** Add or remove daily time slots. You can select specific Qaris for specific times, or let it randomize. 
3. **Auto-Upload Toggle:** In the Settings page, you can globally turn off background automated posts if you only want to use the app manually.
4. **Generate & Post Now:** Click the play button on the dashboard to trigger an immediate manual post. You can choose the Qari and the level of audio editing.

## Audio Editing Modes

When triggering a manual post, you can choose:
- **Heavy Editing:** 0.75x speed + reverb + background rain. Best for standard reciters to bypass copyright.
- **Minor Editing:** 0.90x speed + tiny echo + very soft rain. Best for Othman Al Haddad and Abdur Rahman Mossad.
- **Original Audio:** No processing, just a barely audible nature background.
