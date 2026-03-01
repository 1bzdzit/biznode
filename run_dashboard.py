"""
BizNode Dashboard Launcher
==========================
Run this from the project root to start the owner dashboard.

    python run_dashboard.py

Then open: http://localhost:8080
"""

import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    print("=" * 50)
    print("  BizNode Dashboard")
    print("  http://localhost:7777")
    print("=" * 50)
    uvicorn.run(
        "ui.server:app",
        host="127.0.0.1",
        port=7777,
        reload=False,
        log_level="info",
    )
