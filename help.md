# BizNode Help

## Quick Start

### Setup Wizard

Run the interactive setup to configure your BizNode:

```bash
python setup.py
```

### Setup Commands

| Command | Description |
|---------|-------------|
| `python setup.py` | Run interactive setup wizard |
| `python setup.py --status` | Check configuration status |
| `python setup.py --reinit-db` | Reinitialize database |
| `python setup.py --help` | Show help |

---

## Starting BizNode

### Option 1: Full Stack (Ollama + Qdrant + BizNode)

Start all services together:

```bash
# Start all services (Ollama, Qdrant, BizNode)
docker compose up -d

# Or with more details
docker compose up -d --build
```

### Option 2: External Ollama & Qdrant

If you already have **Ollama on port 11434** and **Qdrant on port 6333** running externally:

```bash
# Start only BizNode agent (connects to external services)
docker compose up -d biznode
```

Or run BizNode directly without Docker:

```bash
# Set environment variables to point to external services
export OLLAMA_URL=http://localhost:11434/api/generate
export OLLAMA_EMBED_URL=http://localhost:11434/api/embeddings
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# Install dependencies and run
pip install -r requirements.txt
python boot.py
```

### Option 3: USB Portable Mode

To run BizNode from a **USB drive**:

```bash
# 1. Copy BizNode folder to USB drive
# 2. On the target computer, navigate to USB drive

cd X:\1bzbiznode  # Windows
# or
cd /media/username/USB/1bzbiznode  # Linux/Mac

# 3. Run setup first
python setup.py

# 4. Start services
docker compose up -d
```

---

## Running Multiple BizNode Instances

**Yes, multiple instances are supported!** Each instance needs:

1. **Unique Telegram Bot Token** - Get from @BotFather
2. **Unique Agent Name** - Different business name
3. **Different Ports** - Avoid port conflicts

### Running Multiple with Docker

Create separate directories for each instance:

```bash
# Instance 1
mkdir biznode1 && cd biznode1
cp ../1bzbiznode/* .
# Edit .env with unique Telegram token
docker compose up -d

# Instance 2 (different ports)
mkdir biznode2 && cd biznode2
cp ../1bzbiznode/* .
# Edit docker-compose.yml to change ports
# Edit .env with different Telegram token
docker compose up -d
```

### Port Configuration for Multiple Instances

Edit `docker-compose.yml` for each instance:

```yaml
# Instance 1
biznode:
  ports:
    - "5000:5000"   # API port

qdrant:
  ports:
    - "6333:6333"  # Vector DB

ollama:
  ports:
    - "11434:11434" # LLM
```

```yaml
# Instance 2 - different ports
biznode:
  ports:
    - "5001:5000"

qdrant:
  ports:
    - "6335:6333"

ollama:
  ports:
    - "11435:11434"
```

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot |
| `/status` | Check system health |
| `/help` | Show this help |
| `/register [business_name]` | Register a new business |
| `/search [query]` | Search memory |

---

## Configuration

Configuration files:
- `.env` - Environment variables
- `config.json` - API configuration  
- `memory/biznode.db` - SQLite database

---

## Troubleshooting

### Bot Not Responding

1. Check if bot token is correct in `.env`
2. Verify the bot has been started (/start in Telegram)
3. Check logs: `docker compose logs biznode`

### Database Issues

1. Reinitialize: `python setup.py --reinit-db`
2. Check SQLite file: `ls -la memory/biznode.db`

### Docker Issues

1. Check status: `docker compose ps`
2. View logs: `docker compose logs -f`
3. Restart: `docker compose restart`

### Port Conflicts

If ports are already in use:

```bash
# Check what's using the port
netstat -ano | findstr "11434"  # Windows
lsof -i :11434                   # Linux/Mac

# Change port in docker-compose.yml
```

---

## Support

For issues and questions, visit the GitHub repository.
