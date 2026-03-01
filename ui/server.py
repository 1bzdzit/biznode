"""
BizNode Owner Dashboard – FastAPI Backend
=========================================
Serves the dashboard HTML and provides REST + WebSocket APIs
that connect directly to existing BizNode services.
"""

import asyncio
import json
import sys
import os
import re
import requests as _requests
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path so BizNode modules resolve
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Direct module loader – bypasses package __init__.py files that may require
# optional dependencies (qdrant_client, langgraph, etc.)
# ---------------------------------------------------------------------------
import importlib.util as _ilu


def _load_direct(module_name: str, rel_path: str):
    abs_path = os.path.join(_PROJECT_ROOT, rel_path)
    spec = _ilu.spec_from_file_location(module_name, abs_path)
    mod = _ilu.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


_db = _load_direct("_biznode_database", "memory/database.py")

get_all_leads       = _db.get_all_leads
get_all_businesses  = _db.get_all_businesses
get_pending_actions = _db.get_pending_actions
get_all_associates  = _db.get_all_associates
get_all_notes       = _db.get_all_notes
resolve_action      = _db.resolve_action
create_lead         = _db.create_lead
get_connection      = _db.get_connection

from services.monitoring import MonitoringService

# RAG graph loaded lazily – requires langgraph + ollama to be running
_rag_graph = None


def _get_rag():
    global _rag_graph
    if _rag_graph is None:
        from graphs.rag_query_graph import run_rag_query as _rq
        _rag_graph = _rq
    return _rag_graph


# ---------------------------------------------------------------------------
# .env file helpers
# ---------------------------------------------------------------------------

_ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")

# Sensitive keys whose values are masked in GET responses
_SENSITIVE = {
    "TELEGRAM_BOT_TOKEN", "SMTP_PASSWORD", "NODE_PASSWORD", "NODE_SIGNING_KEY"
}
_MASK = "••••••••"

# Full settings schema: (key, group, group_label, label, input_type, default, required, hint)
SETTINGS_SCHEMA = [
    # ── Telegram ──────────────────────────────────────────────────────────
    ("TELEGRAM_BOT_TOKEN",  "telegram", "Telegram Bot",
     "Bot Token",           "password", "",             True,
     "From @BotFather on Telegram. Format: 123456789:ABC-DEF..."),
    ("OWNER_TELEGRAM_ID",   "telegram", "Telegram Bot",
     "Owner Telegram ID",   "text",     "",             True,
     "Your numeric Telegram user ID. Send /start to @userinfobot to get it."),

    # ── Ollama / LLM ──────────────────────────────────────────────────────
    ("OLLAMA_URL",          "ollama",   "Ollama / LLM",
     "LLM Endpoint",        "text",     "http://localhost:11434/api/generate", True,
     "Full URL to Ollama generate API. Default works for local install."),
    ("OLLAMA_EMBED_URL",    "ollama",   "Ollama / LLM",
     "Embeddings Endpoint", "text",     "http://localhost:11434/api/embeddings", False,
     "Full URL to Ollama embeddings API. Usually same host as LLM Endpoint."),
    ("LLM_MODEL",           "ollama",   "Ollama / LLM",
     "LLM Model Name",      "text",     "qwen2.5",      True,
     "Name of the model pulled in Ollama (e.g. qwen2.5, llama3, mistral)."),
    ("EMBEDDING_MODEL",     "ollama",   "Ollama / LLM",
     "Embedding Model",     "text",     "nomic-embed-text", False,
     "Model used for vector embeddings. Must be pulled in Ollama."),

    # ── Qdrant ────────────────────────────────────────────────────────────
    ("QDRANT_HOST",         "qdrant",   "Qdrant Vector DB",
     "Qdrant Host",         "text",     "localhost",    False,
     "Hostname where Qdrant is running. localhost for local install."),
    ("QDRANT_PORT",         "qdrant",   "Qdrant Vector DB",
     "Qdrant Port",         "number",   "6333",         False,
     "TCP port for Qdrant REST API. Default is 6333."),

    # ── Email / SMTP ──────────────────────────────────────────────────────
    ("AGENT_EMAIL",         "email",    "Email (SMTP)",
     "Agent Email Address", "text",     "",             False,
     "The email address BizNode sends emails from."),
    ("SMTP_HOST",           "email",    "Email (SMTP)",
     "SMTP Host",           "text",     "smtp.gmail.com", False,
     "SMTP server hostname. For Gmail use smtp.gmail.com."),
    ("SMTP_PORT",           "email",    "Email (SMTP)",
     "SMTP Port",           "number",   "587",          False,
     "SMTP port. 587 for TLS/STARTTLS (Gmail), 465 for SSL."),
    ("SMTP_USER",           "email",    "Email (SMTP)",
     "SMTP Username",       "text",     "",             False,
     "Your email address used to authenticate with the SMTP server."),
    ("SMTP_PASSWORD",       "email",    "Email (SMTP)",
     "SMTP Password",       "password", "",             False,
     "For Gmail, use an App Password (not your account password). Enable 2FA first."),
    ("OWNER_EMAIL",         "email",    "Email (SMTP)",
     "Owner Email",         "text",     "",             False,
     "Email address where BizNode sends owner notifications."),

    # ── Security ──────────────────────────────────────────────────────────
    ("NODE_PASSWORD",       "security", "Security",
     "Node Password",       "password", "",             False,
     "Password used to encrypt the node's cryptographic identity. Set once; do not change."),
    ("NODE_SIGNING_KEY",    "security", "Security",
     "Audit Signing Key",   "password", "biznode-audit-secret", False,
     "Secret used to sign audit log entries. Change from default for production."),

    # ── Advanced ──────────────────────────────────────────────────────────
    ("SQLITE_PATH",         "advanced", "Advanced",
     "SQLite Database Path","text",     "memory/biznode.db", False,
     "Path to the SQLite database file, relative to project root."),
]


def _read_env_file() -> Dict[str, str]:
    """Parse .env file → dict. Returns empty dict if file doesn't exist."""
    result: Dict[str, str] = {}
    if not os.path.exists(_ENV_PATH):
        return result
    with open(_ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                # Strip optional surrounding quotes
                val = val.strip().strip('"').strip("'")
                result[key.strip()] = val
    return result


def _write_env_file(values: Dict[str, str]) -> None:
    """Write a clean, commented .env file from a dict of key→value pairs."""
    groups = {}
    key_to_meta = {}
    for row in SETTINGS_SCHEMA:
        key, grp, grp_label = row[0], row[1], row[2]
        groups.setdefault(grp, grp_label)
        key_to_meta[key] = row

    lines: List[str] = [
        "# BizNode Configuration",
        "# Generated by Dashboard Setup Wizard",
        "# Edit here or via the dashboard at http://localhost:7777",
        "",
    ]

    written_keys = set()
    current_group = None

    for row in SETTINGS_SCHEMA:
        key, grp, grp_label, label, _, default, required, hint = (
            row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]
        )
        if grp != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f"# ── {grp_label} {'─' * max(0, 50 - len(grp_label))}")
            current_group = grp

        val = values.get(key, default)
        req_tag = " (required)" if required else ""
        lines.append(f"# {label}{req_tag}: {hint}")
        lines.append(f"{key}={val}")
        written_keys.add(key)

    # Append any extra keys from the existing file not in our schema
    for key, val in values.items():
        if key not in written_keys:
            lines.append(f"{key}={val}")

    with open(_ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _is_configured() -> bool:
    """True if the two minimum required keys are set."""
    env = _read_env_file()
    return bool(env.get("TELEGRAM_BOT_TOKEN") and env.get("OWNER_TELEGRAM_ID"))


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="BizNode Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

monitoring = MonitoringService()


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Background poller
# ---------------------------------------------------------------------------

_last_seen_id: Optional[str] = None


async def _poll_and_broadcast():
    global _last_seen_id
    while True:
        await asyncio.sleep(3)
        try:
            events = monitoring.get_recent_audit_events(limit=5)
            if events and manager.active:
                newest_id = events[0].get("id")
                if newest_id != _last_seen_id:
                    _last_seen_id = newest_id
                    await manager.broadcast({"type": "activity", "events": events[:5]})
        except Exception:
            pass


@app.on_event("startup")
async def startup_event():
    # Load .env into process environment so services pick up values
    env_vals = _read_env_file()
    for k, v in env_vals.items():
        os.environ.setdefault(k, v)

    try:
        _db.init_db()
    except Exception as e:
        print(f"[dashboard] init_db warning: {e}")

    try:
        _al = _load_direct("_biznode_audit", "services/audit_logger.py")
        _al.AuditLogger()
    except Exception as e:
        print(f"[dashboard] audit_logger init warning: {e}")

    asyncio.create_task(_poll_and_broadcast())


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Serve index.html
# ---------------------------------------------------------------------------

_UI_DIR = Path(__file__).parent


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    html_path = _UI_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Settings endpoints
# ---------------------------------------------------------------------------

@app.get("/api/settings")
async def get_settings():
    """Return schema + current .env values (sensitive fields masked)."""
    env = _read_env_file()

    # Build values dict: apply defaults then overlay .env
    values: Dict[str, str] = {}
    for row in SETTINGS_SCHEMA:
        key, default = row[0], row[5]
        raw = env.get(key, default)
        values[key] = _MASK if (key in _SENSITIVE and raw) else raw

    # Schema for frontend rendering
    schema = [
        {
            "key":       row[0],
            "group":     row[1],
            "group_label": row[2],
            "label":     row[3],
            "type":      row[4],
            "default":   row[5],
            "required":  row[6],
            "hint":      row[7],
            "sensitive": row[0] in _SENSITIVE,
        }
        for row in SETTINGS_SCHEMA
    ]

    configured = _is_configured()
    return JSONResponse({"schema": schema, "values": values, "configured": configured})


@app.post("/api/settings")
async def save_settings(request: Request):
    """Persist form data to .env. Masked values are not overwritten."""
    try:
        data: Dict[str, str] = await request.json()
        existing = _read_env_file()

        for key, val in data.items():
            # If user sent back the mask placeholder, keep the existing secret
            if key in _SENSITIVE and val == _MASK:
                continue
            existing[key] = val

        _write_env_file(existing)

        # Reload into process env so health checks pick up new values immediately
        for k, v in existing.items():
            os.environ[k] = v

        return JSONResponse({"status": "saved", "configured": _is_configured()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/settings/test/{service}")
async def test_service(service: str):
    """Test connectivity to telegram / ollama / qdrant using current saved values."""
    env = _read_env_file()

    try:
        if service == "telegram":
            token = env.get("TELEGRAM_BOT_TOKEN", "")
            if not token:
                return JSONResponse({"ok": False, "message": "Bot token not configured."})
            r = _requests.get(
                f"https://api.telegram.org/bot{token}/getMe", timeout=6
            )
            if r.status_code == 200 and r.json().get("ok"):
                bot = r.json()["result"]
                return JSONResponse({
                    "ok": True,
                    "message": f"Connected! Bot: @{bot.get('username')} ({bot.get('first_name')})"
                })
            return JSONResponse({"ok": False, "message": r.json().get("description", "Unknown error")})

        elif service == "ollama":
            url = env.get("OLLAMA_URL", "http://localhost:11434/api/generate")
            base = url.replace("/api/generate", "").replace("/api/embeddings", "")
            r = _requests.get(f"{base}/api/tags", timeout=6)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                return JSONResponse({
                    "ok": True,
                    "message": f"Connected! Models available: {', '.join(models) or 'none pulled yet'}"
                })
            return JSONResponse({"ok": False, "message": f"HTTP {r.status_code}"})

        elif service == "qdrant":
            host = env.get("QDRANT_HOST", "localhost")
            port = env.get("QDRANT_PORT", "6333")
            r = _requests.get(f"http://{host}:{port}/collections", timeout=6)
            if r.status_code == 200:
                cols = [c["name"] for c in r.json().get("result", {}).get("collections", [])]
                return JSONResponse({
                    "ok": True,
                    "message": f"Connected! Collections: {', '.join(cols) or 'none yet'}"
                })
            return JSONResponse({"ok": False, "message": f"HTTP {r.status_code}"})

        else:
            return JSONResponse({"ok": False, "message": f"Unknown service: {service}"}, status_code=400)

    except Exception as e:
        return JSONResponse({"ok": False, "message": str(e)})


# ---------------------------------------------------------------------------
# Dashboard data endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def get_status():
    try:
        return JSONResponse(monitoring.get_health_status())
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


@app.get("/api/metrics")
async def get_metrics():
    try:
        metrics = monitoring.get_system_metrics()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        metrics["total_leads"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM businesses")
        metrics["total_businesses"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM owner_actions WHERE status = 'pending'")
        metrics["pending_approvals"] = cursor.fetchone()[0]
        conn.close()
        metrics["active_tasks"] = len(monitoring.get_active_tasks())
        return JSONResponse(metrics)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/activities")
async def get_activities(limit: int = 50, event_type: Optional[str] = None):
    try:
        types = [event_type] if event_type else None
        events = monitoring.get_recent_audit_events(event_types=types, limit=limit)
        return JSONResponse(events)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/leads")
async def get_leads(status: Optional[str] = None):
    try:
        return JSONResponse(get_all_leads(status=status))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/businesses")
async def get_businesses():
    try:
        return JSONResponse(get_all_businesses())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/actions/pending")
async def get_pending():
    try:
        return JSONResponse(get_pending_actions())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/actions")
async def get_all_actions(limit: int = 50):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM owner_actions ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return JSONResponse(rows)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/associates")
async def get_associates():
    try:
        return JSONResponse(get_all_associates())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/notes")
async def get_notes():
    try:
        return JSONResponse(get_all_notes())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/reports/summary")
async def get_reports_summary():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
        lead_status = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("""
            SELECT DATE(created_at), COUNT(*) FROM leads
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at) ORDER BY DATE(created_at)
        """)
        lead_trend = [{"day": r[0], "count": r[1]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT DATE(created_at), COUNT(*) FROM owner_actions
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at) ORDER BY DATE(created_at)
        """)
        action_trend = [{"day": r[0], "count": r[1]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT DATE(created_at), COUNT(*) FROM audit_logs
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at) ORDER BY DATE(created_at)
        """)
        audit_trend = [{"day": r[0], "count": r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT source, COUNT(*) FROM leads GROUP BY source")
        lead_sources = {r[0]: r[1] for r in cursor.fetchall()}

        total = sum(lead_status.values()) or 1
        converted = lead_status.get("converted", 0)

        conn.close()

        return JSONResponse({
            "lead_status":      lead_status,
            "lead_trend":       lead_trend,
            "action_trend":     action_trend,
            "audit_trend":      audit_trend,
            "conversion_rate":  round((converted / total) * 100, 1),
            "lead_sources":     lead_sources,
            "total_leads":      total,
            "converted_leads":  converted,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        run_rag_query = _get_rag()
        result = run_rag_query(req.message)
        return JSONResponse({"response": result.get("response", "No response generated.")})
    except Exception as e:
        return JSONResponse({"response": f"Error: {str(e)}"}, status_code=500)


@app.post("/api/actions/{action_id}/approve")
async def approve_action(action_id: int):
    try:
        success = resolve_action(action_id, "approved")
        if not success:
            raise HTTPException(status_code=404, detail="Action not found")
        return JSONResponse({"status": "approved", "action_id": action_id})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/actions/{action_id}/reject")
async def reject_action(action_id: int):
    try:
        success = resolve_action(action_id, "rejected")
        if not success:
            raise HTTPException(status_code=404, detail="Action not found")
        return JSONResponse({"status": "rejected", "action_id": action_id})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        events = monitoring.get_recent_audit_events(limit=20)
        await ws.send_json({"type": "snapshot", "events": events})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
