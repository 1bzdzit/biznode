"""
USB Deployer
============
Copies the BizNode stack to a USB drive for portable use.
Configures relative paths so the node is fully self-contained.
"""

import os
import platform
import shutil
import subprocess
from typing import List, Callable, Optional


# ---------------------------------------------------------------------------
# Drive detection
# ---------------------------------------------------------------------------

def list_removable_drives() -> List[str]:
    """
    Return a list of removable/USB drive paths on the current platform.
    """
    drives: List[str] = []

    if platform.system() == "Windows":
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                if bitmask & (1 << i):
                    drive = f"{letter}:\\"
                    # DRIVE_REMOVABLE = 2
                    if ctypes.windll.kernel32.GetDriveTypeW(drive) == 2:
                        drives.append(drive)
        except Exception:
            pass

    elif platform.system() == "Linux":
        try:
            out = subprocess.check_output(
                ["lsblk", "-o", "NAME,RM,MOUNTPOINT", "-J"],
                timeout=5
            ).decode()
            import json
            data = json.loads(out)
            for dev in data.get("blockdevices", []):
                for child in dev.get("children", []):
                    if child.get("rm") and child.get("mountpoint"):
                        drives.append(child["mountpoint"])
        except Exception:
            pass

    elif platform.system() == "Darwin":
        try:
            volumes = [
                f"/Volumes/{v}"
                for v in os.listdir("/Volumes")
                if v not in ("Macintosh HD",)
            ]
            drives.extend(volumes)
        except Exception:
            pass

    return drives


# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------

# Files/dirs to always exclude from the copy
_EXCLUDE = {
    "__pycache__", ".git", ".env", "memory/biznode.db",
    "memory/qdrant", "memory/ollama", "logs", "dist", "build",
    "*.pyc", "*.egg-info", ".DS_Store",
}


def _should_skip(name: str) -> bool:
    import fnmatch
    for pattern in _EXCLUDE:
        if fnmatch.fnmatch(name, pattern) or name == pattern:
            return True
    return False


def deploy_to_usb(
    source_dir: str,
    usb_path: str,
    config: dict,
    log: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Copy the BizNode project to a USB drive and configure it for portable use.

    config keys used:
      TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_ID,
      ollama_port, qdrant_port, dashboard_port,
      llm_model, embedding_model, ...

    Creates:
      <usb_path>/biznode/
        .env
        docker-compose.yml  (relative paths, portable)
        memory/             (empty, created fresh)
        identity/
        ... (source files)
    """

    def _log(msg: str):
        if log:
            log(msg)
        else:
            print(msg)

    dest = os.path.join(usb_path, "biznode")
    _log(f"Deploying to: {dest}")

    # 1. Create destination structure
    os.makedirs(dest, exist_ok=True)
    for sub in ("memory", "logs", "identity"):
        os.makedirs(os.path.join(dest, sub), exist_ok=True)

    # 2. Copy project files
    _log("Copying project files…")
    for item in os.listdir(source_dir):
        if _should_skip(item):
            _log(f"  Skipping: {item}")
            continue
        src_item = os.path.join(source_dir, item)
        dst_item = os.path.join(dest, item)
        try:
            if os.path.isdir(src_item):
                shutil.copytree(src_item, dst_item, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(*_EXCLUDE))
                _log(f"  Copied dir: {item}")
            else:
                shutil.copy2(src_item, dst_item)
                _log(f"  Copied: {item}")
        except Exception as e:
            _log(f"  Warning: could not copy {item}: {e}")

    # 3. Write .env with USB-relative paths
    from installer.core.env_writer import write_env
    env_values = {
        "TELEGRAM_BOT_TOKEN":  config.get("TELEGRAM_BOT_TOKEN", ""),
        "OWNER_TELEGRAM_ID":   config.get("OWNER_TELEGRAM_ID", ""),
        "OLLAMA_URL":          f"http://localhost:{config.get('ollama_port', 11434)}/api/generate",
        "OLLAMA_EMBED_URL":    f"http://localhost:{config.get('ollama_port', 11434)}/api/embeddings",
        "QDRANT_HOST":         "localhost",
        "QDRANT_PORT":         str(config.get("qdrant_port", 6333)),
        "LLM_MODEL":           config.get("LLM_MODEL", "qwen2.5"),
        "EMBEDDING_MODEL":     config.get("EMBEDDING_MODEL", "nomic-embed-text"),
        "SQLITE_PATH":         "./memory/biznode.db",
        "DATA_DIR":            "./memory",
    }
    env_path = os.path.join(dest, ".env")
    write_env(env_path, env_values)
    _log("Wrote .env")

    # 4. Write portable docker-compose.yml with relative data paths
    from installer.core.compose_builder import build_compose, write_compose
    compose = build_compose(
        ollama_port=config.get("ollama_port", 11434),
        qdrant_port=config.get("qdrant_port", 6333),
        dashboard_port=config.get("dashboard_port", 7777),
        data_dir="./memory",
        include_ollama=config.get("include_ollama", True),
        include_qdrant=config.get("include_qdrant", True),
        use_gpu=config.get("use_gpu", False),
    )
    write_compose(os.path.join(dest, "docker-compose.yml"), compose)
    _log("Wrote docker-compose.yml (portable)")

    # 5. Write a README for USB users
    readme = (
        "# BizNode — Portable Node\n\n"
        "## Quick Start\n\n"
        "1. Install Docker Desktop\n"
        "2. Open a terminal in this folder\n"
        "3. Run: `docker compose up -d`\n"
        "4. Open browser: http://localhost:7777\n\n"
        "## Configuration\n\n"
        "Edit `.env` to update your Telegram bot token or other settings.\n"
    )
    with open(os.path.join(dest, "README_USB.md"), "w") as f:
        f.write(readme)
    _log("Wrote README_USB.md")

    _log(f"\n✓ USB deployment complete → {dest}")
