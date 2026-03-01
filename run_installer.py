"""
BizNode Installer Launcher
==========================
Run this from the project root:

    python run_installer.py

Requires PySide6:
    pip install PySide6
"""

import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _check_pyside6():
    try:
        import PySide6
        return True
    except ImportError:
        return False


def _check_requests():
    try:
        import requests
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    missing = []
    if not _check_pyside6():
        missing.append("PySide6")
    if not _check_requests():
        missing.append("requests")

    if missing:
        print("=" * 55)
        print("  BizNode Installer — Missing Dependencies")
        print("=" * 55)
        print(f"\n  Missing: {', '.join(missing)}\n")
        print("  Install with:")
        print(f"    pip install {' '.join(missing)}")
        print("\n  Then re-run:  python run_installer.py\n")
        sys.exit(1)

    print("Starting BizNode Installer GUI…")
    from installer.main import main
    main()
