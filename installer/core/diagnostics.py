"""
System Diagnostics
==================
Checks prerequisites: Python, Docker, WSL, RAM, disk space, and port availability.
All check functions return a dict:
  { "ok": bool, "warn": bool, "label": str, "detail": str }
"""

import os
import platform
import shutil
import socket
import subprocess
import sys
from typing import Dict, Any, List


Result = Dict[str, Any]


def _result(ok: bool, label: str, detail: str, warn: bool = False) -> Result:
    return {"ok": ok, "warn": warn, "label": label, "detail": detail}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_python() -> Result:
    ver = sys.version_info
    ok = ver >= (3, 10)
    s = f"{ver.major}.{ver.minor}.{ver.micro}"
    return _result(ok, "Python ≥ 3.10", f"Found {s}" if ok else f"Found {s} — need 3.10+")


def check_docker_installed() -> Result:
    path = shutil.which("docker")
    if not path:
        return _result(False, "Docker installed", "docker not found in PATH")
    try:
        out = subprocess.check_output(["docker", "--version"], stderr=subprocess.DEVNULL,
                                      timeout=5).decode().strip()
        return _result(True, "Docker installed", out)
    except Exception as e:
        return _result(False, "Docker installed", str(e))


def check_docker_running() -> Result:
    try:
        subprocess.check_output(["docker", "info"], stderr=subprocess.DEVNULL, timeout=8)
        return _result(True, "Docker daemon running", "Docker engine is active")
    except subprocess.CalledProcessError:
        return _result(False, "Docker daemon running",
                       "Docker is installed but not running — start Docker Desktop")
    except FileNotFoundError:
        return _result(False, "Docker daemon running", "docker not found in PATH")
    except Exception as e:
        return _result(False, "Docker daemon running", str(e))


def check_wsl() -> Result:
    if platform.system() != "Windows":
        return _result(True, "WSL (N/A)", "Not required on non-Windows", warn=False)
    try:
        out = subprocess.check_output(["wsl", "--list", "--verbose"],
                                      stderr=subprocess.DEVNULL, timeout=6).decode()
        return _result(True, "WSL2 available", "WSL2 detected")
    except FileNotFoundError:
        return _result(False, "WSL2 available",
                       "WSL not found — Docker Desktop needs WSL2 on Windows", warn=True)
    except Exception as e:
        return _result(False, "WSL2 available", str(e), warn=True)


def check_ram() -> Result:
    gb: float = 0.0
    try:
        if platform.system() == "Windows":
            import ctypes
            mem_status = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(
                ctypes.byref(mem_status))
            gb = mem_status.value / 1024 / 1024
        elif platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        gb = int(line.split()[1]) / 1024 / 1024
                        break
        elif platform.system() == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"],
                                          timeout=3).decode()
            gb = int(out.strip()) / 1024 ** 3
    except Exception:
        pass

    if gb < 1:
        return _result(True, "RAM", "Could not detect RAM (continuing)", warn=True)

    ok = gb >= 8
    warn = 4 <= gb < 8
    return _result(ok or warn, "RAM ≥ 8 GB", f"{gb:.1f} GB detected",
                   warn=(not ok and warn))


def check_disk_space(path: str = ".") -> Result:
    try:
        stat = shutil.disk_usage(path)
        free_gb = stat.free / 1024 ** 3
        ok = free_gb >= 10
        return _result(ok, "Disk space ≥ 10 GB free",
                       f"{free_gb:.1f} GB free on target drive",
                       warn=not ok)
    except Exception as e:
        return _result(True, "Disk space", f"Could not check: {e}", warn=True)


def check_nvidia_gpu() -> Result:
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=name",
                                       "--format=csv,noheader"],
                                      stderr=subprocess.DEVNULL, timeout=6).decode().strip()
        return _result(True, "NVIDIA GPU", f"Found: {out.splitlines()[0]}")
    except Exception:
        return _result(True, "NVIDIA GPU", "Not detected — CPU mode will be used", warn=True)


def check_port_available(port: int, label: str) -> Result:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        in_use = s.connect_ex(("127.0.0.1", port)) == 0
    status = "in use (service may be reusable)" if in_use else "available"
    return _result(True, f"Port {port} ({label})", status, warn=in_use)


# ---------------------------------------------------------------------------
# Run all checks
# ---------------------------------------------------------------------------

def run_all_checks(deploy_path: str = ".") -> List[Result]:
    return [
        check_python(),
        check_docker_installed(),
        check_docker_running(),
        check_wsl(),
        check_ram(),
        check_disk_space(deploy_path),
        check_nvidia_gpu(),
        check_port_available(11434, "Ollama"),
        check_port_available(6333, "Qdrant"),
        check_port_available(7777, "Dashboard"),
    ]
