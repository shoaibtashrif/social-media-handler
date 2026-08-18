#!/bin/bash
# start.sh
# Automated setup and run script for Quran Automator

set -e # Exit on any error

echo "======================================"
echo "🕌 Quran Automator Setup & Start"
echo "======================================"

# 1. Install system dependencies if missing
echo "Checking system dependencies..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚙️ Installing ffmpeg..."
    sudo apt-get update
    sudo apt-get install -y ffmpeg
else
    echo "✅ ffmpeg is already installed."
fi

if ! command -v yt-dlp &> /dev/null; then
    echo "⚙️ Installing yt-dlp..."
    sudo wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp
    sudo chmod a+rx /usr/local/bin/yt-dlp
else
    echo "✅ yt-dlp is already installed."
fi

# 2. Python Environment Setup
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    echo "⚙️ Creating virtual environment 'venv'..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# 3. Install Python requirements
echo "⚙️ Installing Python dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found! The application might fail if environment variables are missing."
    echo "   Please create a .env file with your API keys based on README instructions."
    echo ""
    read -p "Press Enter to try starting anyway, or Ctrl+C to abort..."
fi

# 5. Run the application
echo "======================================"
echo "🚀 Starting Server in Background..."
echo "======================================"
nohup python3 run.py > main.log 2>&1 &
echo "✅ Server detached! Logs are being written to main.log"
