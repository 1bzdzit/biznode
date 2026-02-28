import os
import getpass
import time
import requests
from identity.identity import generate_identity, identity_exists

# Standalone mode: read endpoints from env (set in .env) or use native defaults
OLLAMA_HOST = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/api/generate").rstrip("/")
QDRANT_HOST = f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')}"

def wait_for_services():
    """Wait until Ollama and Qdrant are healthy before starting the bot."""
    services = {
        "Ollama": f"{OLLAMA_HOST}",
        "Qdrant": f"{QDRANT_HOST}/healthz",
    }
    for name, url in services.items():
        print(f"Waiting for {name} at {url}...")
        for attempt in range(30):
            try:
                requests.get(url, timeout=2)
                print(f"  {name} is ready.")
                break
            except Exception:
                time.sleep(2)
        else:
            print(f"  WARNING: {name} did not become ready after 60s. Continuing anyway.")

def boot():
    print("=== BizNode Boot (Standalone Mode) ===")

    # Read password securely — never hardcode
    password_env = os.getenv("NODE_PASSWORD")
    if password_env:
        PASSWORD = password_env.encode()
    else:
        PASSWORD = getpass.getpass("Enter node password: ").encode()

    if not identity_exists():
        print("Generating new node identity...")
        node_id = generate_identity(PASSWORD)
        print("Node ID:", node_id)
    else:
        print("Identity exists.")

    # Standalone: skip Docker launch — Ollama and Qdrant are already running natively
    print("Skipping Docker launch (standalone mode — using native Ollama + Qdrant).")

    print("Waiting for services to be ready...")
    wait_for_services()

    print("\nNode running on:")
    print(f"  Ollama : {OLLAMA_HOST}")
    print(f"  Qdrant : {QDRANT_HOST}")

if __name__ == "__main__":
    boot()
