"""
Docker Compose Builder
======================
Generates a docker-compose.yml dynamically based on:
  - Which services to include (Ollama, Qdrant, bot)
  - Port assignments
  - Data directory (local or USB)
  - GPU availability
"""

import os
from typing import Dict, Any


# ---------------------------------------------------------------------------
# Base service templates
# ---------------------------------------------------------------------------

def _qdrant_service(port: int, data_dir: str) -> Dict:
    return {
        "image": "qdrant/qdrant",
        "ports": [f"{port}:6333", f"{port + 1}:6334"],
        "volumes": [f"{data_dir}/qdrant:/qdrant/storage"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost:6333/healthz"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 10,
            "start_period": "15s",
        },
    }


def _ollama_service(port: int, data_dir: str, use_gpu: bool = False) -> Dict:
    svc: Dict[str, Any] = {
        "image": "ollama/ollama",
        "ports": [f"{port}:11434"],
        "volumes": [f"{data_dir}/ollama:/root/.ollama"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", f"http://localhost:11434"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 10,
            "start_period": "30s",
        },
    }
    if use_gpu:
        svc["deploy"] = {
            "resources": {
                "reservations": {
                    "devices": [{"capabilities": ["gpu"]}]
                }
            }
        }
    return svc


def _bot_service(
    ollama_host: str,
    ollama_port: int,
    qdrant_host: str,
    qdrant_port: int,
    dashboard_port: int,
    data_dir: str,
    depends_on_qdrant: bool = True,
    depends_on_ollama: bool = True,
) -> Dict:
    depends: Dict[str, Dict] = {}
    if depends_on_qdrant:
        depends["qdrant"] = {"condition": "service_healthy"}
    if depends_on_ollama:
        depends["ollama"] = {"condition": "service_healthy"}

    svc: Dict[str, Any] = {
        "build": {"context": ".", "dockerfile": "docker/bot/Dockerfile"},
        "ports": [f"{dashboard_port}:7777"],
        "environment": [
            "TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}",
            "OWNER_TELEGRAM_ID=${OWNER_TELEGRAM_ID}",
            f"OLLAMA_URL=http://{ollama_host}:{ollama_port}/api/generate",
            f"OLLAMA_EMBED_URL=http://{ollama_host}:{ollama_port}/api/embeddings",
            f"QDRANT_HOST={qdrant_host}",
            f"QDRANT_PORT={qdrant_port}",
            "LLM_MODEL=${LLM_MODEL:-qwen2.5}",
            "EMBEDDING_MODEL=${EMBEDDING_MODEL:-nomic-embed-text}",
            "EMBEDDING_SIZE=768",
            "SQLITE_PATH=/app/memory/biznode.db",
            "SMTP_HOST=${SMTP_HOST:-}",
            "SMTP_PORT=${SMTP_PORT:-587}",
            "SMTP_USER=${SMTP_USER:-}",
            "SMTP_PASSWORD=${SMTP_PASSWORD:-}",
            "AGENT_EMAIL=${AGENT_EMAIL:-}",
            "AUTONOMY_LEVEL=${AUTONOMY_LEVEL:-1}",
        ],
        "volumes": [
            "./identity:/app/identity:ro",
            f"{data_dir}/db:/app/memory",
            "./logs:/app/logs",
        ],
        "restart": "unless-stopped",
    }
    if depends:
        svc["depends_on"] = depends
    return svc


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_compose(
    ollama_port: int = 11434,
    qdrant_port: int = 6333,
    dashboard_port: int = 7777,
    data_dir: str = "./memory",
    include_ollama: bool = True,
    include_qdrant: bool = True,
    external_ollama_host: str = "localhost",
    external_qdrant_host: str = "localhost",
    use_gpu: bool = False,
) -> Dict:
    """
    Build a docker-compose dict.

    When include_ollama=False, the bot connects to an external Ollama.
    When include_qdrant=False, the bot connects to an external Qdrant.
    """
    services: Dict[str, Any] = {}

    # Determine connection targets
    if include_qdrant:
        services["qdrant"] = _qdrant_service(qdrant_port, data_dir)
        qdrant_host = "qdrant"
        actual_qdrant_port = 6333  # internal port inside compose network
    else:
        qdrant_host = external_qdrant_host
        actual_qdrant_port = qdrant_port

    if include_ollama:
        services["ollama"] = _ollama_service(ollama_port, data_dir, use_gpu)
        ollama_host = "ollama"
        actual_ollama_port = 11434
    else:
        ollama_host = external_ollama_host
        actual_ollama_port = ollama_port

    services["bot"] = _bot_service(
        ollama_host=ollama_host,
        ollama_port=actual_ollama_port,
        qdrant_host=qdrant_host,
        qdrant_port=actual_qdrant_port,
        dashboard_port=dashboard_port,
        data_dir=data_dir,
        depends_on_qdrant=include_qdrant,
        depends_on_ollama=include_ollama,
    )

    return {"version": "3.9", "services": services}


def write_compose(path: str, compose: Dict) -> None:
    """Write compose dict to YAML file."""
    try:
        import yaml
        content = yaml.dump(compose, default_flow_style=False, sort_keys=False)
    except ImportError:
        # Fallback: manual YAML rendering (basic)
        content = _dict_to_yaml(compose, indent=0)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# docker-compose.yml — Generated by BizNode Installer\n")
        f.write(content)


def _dict_to_yaml(obj, indent: int = 0) -> str:
    """Minimal YAML serialiser (fallback if PyYAML not installed)."""
    lines = []
    pad = "  " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                lines.append(_dict_to_yaml(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {v}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    prefix = f"{pad}- " if first else f"{pad}  "
                    first = False
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        lines.append(_dict_to_yaml(v, indent + 2))
                    else:
                        lines.append(f"{prefix}{k}: {v}")
            else:
                lines.append(f"{pad}- {item}")
    else:
        lines.append(f"{pad}{obj}")
    return "\n".join(lines)
