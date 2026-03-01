"""
Service Detector
================
Detects running services (Ollama, Qdrant, BizNode), checks port availability,
finds free ports, and manages the services.json registry file.
"""

import json
import os
import socket
import subprocess
from typing import Dict, Any, Optional, List

import requests


# ---------------------------------------------------------------------------
# Port utilities
# ---------------------------------------------------------------------------

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if something is bound to the port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_free_port(start: int, max_range: int = 100) -> int:
    """Return next free port starting from `start`."""
    for port in range(start, start + max_range):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"No free port found in range {start}–{start + max_range}")


# ---------------------------------------------------------------------------
# Service detection
# ---------------------------------------------------------------------------

def detect_ollama(host: str = "localhost", port: int = 11434) -> Dict[str, Any]:
    """
    Detect Ollama. Returns dict with:
      running, port, version, models
    """
    result = {"running": False, "port": port, "host": host, "models": [], "version": ""}
    try:
        r = requests.get(f"http://{host}:{port}/api/tags", timeout=3)
        if r.status_code < 500:
            result["running"] = True
            data = r.json()
            result["models"] = [m["name"] for m in data.get("models", [])]
        # Try version
        rv = requests.get(f"http://{host}:{port}/api/version", timeout=3)
        if rv.ok:
            result["version"] = rv.json().get("version", "")
    except Exception:
        pass
    return result


def detect_qdrant(host: str = "localhost", port: int = 6333) -> Dict[str, Any]:
    """
    Detect Qdrant. Returns dict with:
      running, port, collections
    """
    result = {"running": False, "port": port, "host": host, "collections": []}
    try:
        r = requests.get(f"http://{host}:{port}/collections", timeout=3)
        if r.status_code == 200:
            result["running"] = True
            data = r.json()
            result["collections"] = [
                c["name"] for c in data.get("result", {}).get("collections", [])
            ]
    except Exception:
        pass
    return result


def detect_biznode_dashboard(port: int = 7777) -> Dict[str, Any]:
    """Detect a running BizNode dashboard instance."""
    result = {"running": False, "port": port}
    try:
        r = requests.get(f"http://127.0.0.1:{port}/api/status", timeout=3)
        if r.status_code == 200:
            result["running"] = True
            result["health"] = r.json()
    except Exception:
        pass
    return result


def detect_docker_containers() -> List[Dict[str, str]]:
    """
    List running Docker containers relevant to BizNode.
    Returns list of dicts: {name, image, ports, status}
    """
    containers = []
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format",
             "{{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"],
            stderr=subprocess.DEVNULL, timeout=8
        ).decode().strip()
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 4:
                name = parts[0]
                if any(kw in name.lower() for kw in
                       ("ollama", "qdrant", "biznode", "bot")):
                    containers.append({
                        "name":   parts[0],
                        "image":  parts[1],
                        "ports":  parts[2],
                        "status": parts[3],
                    })
    except Exception:
        pass
    return containers


def detect_all(dashboard_port: int = 7777) -> Dict[str, Any]:
    """
    Run all service detection and return a combined result dict.
    """
    ollama = detect_ollama()
    qdrant = detect_qdrant()
    biznode = detect_biznode_dashboard(dashboard_port)
    containers = detect_docker_containers()

    return {
        "ollama":     ollama,
        "qdrant":     qdrant,
        "biznode":    biznode,
        "containers": containers,
    }


# ---------------------------------------------------------------------------
# Services registry (services.json)
# ---------------------------------------------------------------------------

_DEFAULT_REGISTRY = {
    "ollama_host":     "localhost",
    "ollama_port":     11434,
    "qdrant_host":     "localhost",
    "qdrant_port":     6333,
    "dashboard_port":  7777,
    "mode":            "isolated",
    "data_dir":        "./memory",
}


def load_registry(path: str) -> Dict[str, Any]:
    """Load services.json; returns defaults if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {**_DEFAULT_REGISTRY, **json.load(f)}
    except FileNotFoundError:
        return dict(_DEFAULT_REGISTRY)
    except Exception:
        return dict(_DEFAULT_REGISTRY)


def save_registry(path: str, data: Dict[str, Any]) -> None:
    """Save services.json."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({**_DEFAULT_REGISTRY, **data}, f, indent=2)


# ---------------------------------------------------------------------------
# Smart port assignment
# ---------------------------------------------------------------------------

def assign_ports(
    want_ollama_port: int = 11434,
    want_qdrant_port: int = 6333,
    want_dashboard_port: int = 7777,
    ollama_running: bool = False,
    qdrant_running: bool = False,
) -> Dict[str, int]:
    """
    Determine the ports to use for each service.
    If a port is in use by a non-reused service, find the next free one.
    """
    ports: Dict[str, int] = {}

    # Ollama
    if ollama_running:
        ports["ollama"] = want_ollama_port  # reuse as-is
    elif is_port_in_use(want_ollama_port):
        ports["ollama"] = find_free_port(want_ollama_port + 1)
    else:
        ports["ollama"] = want_ollama_port

    # Qdrant
    if qdrant_running:
        ports["qdrant"] = want_qdrant_port
    elif is_port_in_use(want_qdrant_port):
        ports["qdrant"] = find_free_port(want_qdrant_port + 2)
    else:
        ports["qdrant"] = want_qdrant_port

    # Dashboard
    if is_port_in_use(want_dashboard_port):
        ports["dashboard"] = find_free_port(want_dashboard_port + 1)
    else:
        ports["dashboard"] = want_dashboard_port

    return ports
