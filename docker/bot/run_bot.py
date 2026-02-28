"""
BizNode Telegram Bot
====================
Connects to local Ollama (LLM) and Qdrant (vector memory) to provide
a RAG-augmented AI assistant via Telegram.

Environment variables (set in docker-compose.yml):
  BOT_TOKEN    - Telegram bot token (required)
  OLLAMA_URL   - Ollama generate endpoint
  QDRANT_URL   - Qdrant base URL
  OLLAMA_MODEL - Model name (default: qwen2.5)
"""

import os
import sys
import logging
import time
from collections import defaultdict

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("biznode.bot")

# ── Config from environment ───────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN or BOT_TOKEN == "YOUR_TOKEN":
    logger.critical("BOT_TOKEN is not set. Set it in .env and restart.")
    sys.exit(1)

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434/api/generate")
QDRANT_URL   = os.getenv("QDRANT_URL",   "http://localhost:6333")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")

QDRANT_COLLECTION = "biznode_memory"
EMBED_DIM = int(os.getenv("EMBEDDING_SIZE", "768"))  # nomic-embed-text output dimension

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Allow at most MAX_REQUESTS per user per WINDOW_SECONDS
MAX_REQUESTS = 5
WINDOW_SECONDS = 60
_user_request_times: dict[int, list[float]] = defaultdict(list)

def is_rate_limited(user_id: int) -> bool:
    now = time.time()
    times = _user_request_times[user_id]
    # Remove timestamps outside the window
    _user_request_times[user_id] = [t for t in times if now - t < WINDOW_SECONDS]
    if len(_user_request_times[user_id]) >= MAX_REQUESTS:
        return True
    _user_request_times[user_id].append(now)
    return False

# ── Embedding helper ──────────────────────────────────────────────────────────
def embed_text(text: str) -> list[float] | None:
    """Generate a sentence embedding using a local model via Ollama embeddings API."""
    try:
        r = requests.post(
            OLLAMA_URL.replace("/api/generate", "/api/embeddings"),
            json={"model": OLLAMA_MODEL, "prompt": text},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("embedding")
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None

# ── Qdrant helpers ────────────────────────────────────────────────────────────
def ensure_qdrant_collection():
    """Create the Qdrant collection if it does not exist."""
    try:
        r = requests.get(f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}", timeout=5)
        if r.status_code == 404:
            requests.put(
                f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}",
                json={"vectors": {"size": EMBED_DIM, "distance": "Cosine"}},
                timeout=10,
            )
            logger.info("Created Qdrant collection '%s'", QDRANT_COLLECTION)
    except Exception as e:
        logger.warning("Could not ensure Qdrant collection: %s", e)


def search_memory(query_vector: list[float], top_k: int = 3) -> list[str]:
    """Search Qdrant for the most relevant stored messages."""
    try:
        r = requests.post(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/search",
            json={"vector": query_vector, "limit": top_k, "with_payload": True},
            timeout=10,
        )
        r.raise_for_status()
        results = r.json().get("result", [])
        return [hit["payload"].get("text", "") for hit in results if hit.get("payload")]
    except Exception as e:
        logger.warning("Qdrant search failed: %s", e)
        return []


def store_in_memory(text: str, vector: list[float], user_id: int):
    """Store a message and its embedding in Qdrant."""
    try:
        import hashlib, struct
        # Derive a deterministic uint64 point ID from text hash
        h = hashlib.sha256(f"{user_id}:{text}".encode()).digest()
        point_id = struct.unpack(">Q", h[:8])[0]
        requests.put(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points",
            json={
                "points": [
                    {
                        "id": point_id,
                        "vector": vector,
                        "payload": {"text": text, "user_id": user_id},
                    }
                ]
            },
            timeout=10,
        )
    except Exception as e:
        logger.warning("Qdrant store failed: %s", e)

# ── LLM helper ────────────────────────────────────────────────────────────────
def query_llm(prompt: str, context_snippets: list[str] | None = None) -> str:
    """Query Ollama with optional RAG context injected into the prompt."""
    if context_snippets:
        context_block = "\n".join(f"- {s}" for s in context_snippets if s)
        full_prompt = (
            f"Relevant context from memory:\n{context_block}\n\n"
            f"User question: {prompt}\n\nAnswer:"
        )
    else:
        full_prompt = prompt

    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": full_prompt, "stream": False},
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("response", "No response from AI.")
    except requests.exceptions.Timeout:
        return "⏳ AI is taking too long to respond. Please try again."
    except requests.exceptions.ConnectionError:
        return "❌ AI service is unavailable. Please try again later."
    except Exception as e:
        logger.error("LLM query failed: %s", e)
        return f"❌ Error: {e}"

# ── Sanitization ──────────────────────────────────────────────────────────────
def sanitize_input(text: str) -> str:
    """Basic input sanitization — strip and truncate."""
    return text.strip()[:2000]

# ── Telegram handlers ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *BizNode AI Node Active*\n\n"
        "Commands:\n"
        "  /ask <question> — Ask the AI\n"
        "  /memory — Show memory status\n"
        "  /help — Show this message",
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def memory_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Qdrant collection info."""
    try:
        r = requests.get(f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}", timeout=5)
        data = r.json()
        count = data.get("result", {}).get("points_count", "unknown")
        await update.message.reply_text(f"🧠 Memory: {count} stored entries in Qdrant.")
    except Exception as e:
        await update.message.reply_text(f"❌ Memory unavailable: {e}")


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ask command with RAG pipeline."""
    user_id = update.effective_user.id

    if is_rate_limited(user_id):
        await update.message.reply_text(
            f"⚠️ Rate limit: max {MAX_REQUESTS} requests per {WINDOW_SECONDS}s. Please wait."
        )
        return

    # Extract question from command args or message text
    if context.args:
        user_text = sanitize_input(" ".join(context.args))
    else:
        await update.message.reply_text("Usage: /ask <your question>")
        return

    if not user_text:
        await update.message.reply_text("Please provide a question after /ask.")
        return

    await update.message.reply_text("🔍 Thinking...")

    # RAG: embed → search memory → inject context → query LLM
    vector = embed_text(user_text)
    context_snippets: list[str] = []
    if vector:
        context_snippets = search_memory(vector)
        store_in_memory(user_text, vector, user_id)

    response = query_llm(user_text, context_snippets)
    await update.message.reply_text(response)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages (non-command) as implicit /ask."""
    user_id = update.effective_user.id

    if is_rate_limited(user_id):
        await update.message.reply_text(
            f"⚠️ Rate limit: max {MAX_REQUESTS} requests per {WINDOW_SECONDS}s."
        )
        return

    user_text = sanitize_input(update.message.text or "")
    if not user_text:
        return

    vector = embed_text(user_text)
    context_snippets: list[str] = []
    if vector:
        context_snippets = search_memory(vector)
        store_in_memory(user_text, vector, user_id)

    response = query_llm(user_text, context_snippets)
    await update.message.reply_text(response)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ensure_qdrant_collection()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("memory", memory_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("BizNode bot starting...")
    app.run_polling()
