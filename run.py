#!/usr/bin/env python3
"""
run.py — Start the Quran Social Media Automation server.

Usage:
    python run.py

All config comes from .env — just update that file on a new machine.
"""
import os
import sys

# Ensure project root is in path when running as a script
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8009))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"""
╔══════════════════════════════════════════════════════╗
║       🕌  Quran Social Media Automation              ║
║──────────────────────────────────────────────────────║
║  Server  : http://{host}:{port}
║  Docs    : http://127.0.0.1:{port}/docs
║  Health  : http://127.0.0.1:{port}/health
║  Trigger : POST http://127.0.0.1:{port}/api/post-now/sync
╚══════════════════════════════════════════════════════╝
""")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
