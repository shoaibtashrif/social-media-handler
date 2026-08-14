# Social Media Handler (Automated Poster)

An automated background service that dynamically generates and posts Quranic recitation videos to Instagram Reels, Facebook Pages, and YouTube Shorts. 

## 🚀 Deployment Guide (Always-on Machine)

Follow these instructions to deploy this application on a remote server or always-on machine.

### 1. Prerequisites
- **Python 3.10+**
- **FFmpeg** installed and accessible in the system path (`sudo apt update && sudo apt install ffmpeg`)
- **Git**

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd social-media-handler
```

### 3. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Setup Configuration & Secrets
Since secrets are securely ignored by Git, you must manually add the following three things to your remote server:

1. **`.env` file**: Create a `.env` file in the root directory and configure all API keys, page names, and preferences (refer to your local `.env` file).
2. **`youtube_token.json`**: Upload your local `youtube_token.json` to the remote server's root directory. This provides authorized access to your YouTube channel.
3. **Media (`upload_media/`)**: Create an `upload_media/` directory in the root folder and place your background `.jpg`/`.png` images inside it.

### 5. Running the Automation
You can run the automation using a persistent background tool like `screen`, `tmux`, or `systemd`.

**Using nohup (Simple):**
```bash
nohup python3 run.py > app.log 2>&1 &
```

**Using Systemd (Recommended for auto-restart on server reboot):**
1. Create a service file: `sudo nano /etc/systemd/system/quran-poster.service`
2. Add the following (update the paths to match your server):
```ini
[Unit]
Description=Quran Video Auto Poster
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/social-media-handler
ExecStart=/path/to/social-media-handler/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```
3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable quran-poster
sudo systemctl start quran-poster
```

### 6. Updating the Code
When you make changes locally and push them to GitHub, simply update your server by running:
```bash
cd /path/to/social-media-handler
git pull origin main
# Restart the app:
sudo systemctl restart quran-poster
```
