# BizNode — Autonomous AI Business Agent

A portable, decentralized AI business node that runs from a USB device. Each node has its own cryptographic identity, local LLM (Ollama Qwen2.5), vector memory (Qdrant), SQLite database, LangGraph orchestration, Telegram interface, and optional blockchain integration.

---

## ✨ AI Obsidian Memory Engine

BizNode now includes an **AI Obsidian Memory Engine** - a self-building knowledge graph that:

- **Auto-summarizes** business profiles using LLM
- **Auto-embeds** content into semantic vector space
- **Auto-links** related businesses through similarity scoring
- **Auto-tags** business domains
- **Maintains** a knowledge graph with backlinks
- **Provides RAG context** to Telegram queries

This is **NOT just RAG** - it's an intelligent business memory that learns and grows.

---

## 🚀 Automation Layer (NEW!)

BizNode now includes a powerful **Automation Layer** that transforms it into a true autonomous digital operator:

- **Task Planner** - AI breaks down goals into executable steps
- **Tool Registry** - Database, email, file, Telegram, memory, webhook tools
- **Agent Loop** - Autonomous planning → execution → evaluation → learning
- **Background Scheduler** - Recurring tasks and automation
- **Learning System** - Remembers past executions for improvement

```python
from automation import run_agent_goal

# Run an autonomous goal
result = run_agent_goal(
    user_id="user123",
    goal="Check overdue invoices and send reminders"
)
```

---

## Quick Start

### 1. Setup

```bash
# Copy and fill in secrets
cp .env.example .env
# Edit .env: set TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_ID, SMTP settings
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Services (Docker)

```bash
docker-compose up -d
```

This starts:
- **Ollama** (Qwen2.5 4GB) - Local LLM
- **Qdrant** - Vector database
- **BizNode Agent** - Main application

### 4. Initialize Database

```bash
python -c "from memory.database import init_db; init_db()"
```

### 5. Configure Agent Identity

```python
from memory.database import save_agent_identity

identity = {
    "agent_name": "MyBizNode",
    "agent_email": "ai@mybiznode.1bz",
    "telegram_bot_token": "YOUR_TOKEN",
    "owner_telegram_id": "YOUR_TELEGRAM_ID",
    "owner_email": "you@example.com",
    "autonomy_level": 1
}
save_agent_identity(identity)
```

---

## Architecture

```
Telegram Channel (Marketing / Public)
        ↓
Telegram Bot (Independent API Key)
        ↓
LangGraph Autonomous Agent
        ↓
Ollama (Qwen2.5 4GB) ← Reasoning + Decision Intelligence
        ↓
AI Obsidian Memory Layer
    ├── SQLite (Structured Data)
    ├── Qdrant (Semantic Memory)
    └── Auto-Link Engine
        ↓
Email Service (Owner Notifications)
        ↓
1bz Associate Network (Optional)
```

### Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Ollama (Qwen2.5) | Reasoning & decision intelligence |
| **Vector DB** | Qdrant | Semantic memory storage |
| **State DB** | SQLite | Structured data & metadata |
| **Orchestration** | LangGraph | Workflow automation |
| **Interface** | Telegram Bot | User interaction |
| **Memory** | AI Obsidian Layer | Self-building knowledge graph |

---

## Directory Structure

```
1bzbiznode/
├── boot.py                     ← Main entry point
├── .env.example                ← Environment template
├── .gitignore
├── requirements.txt             ← Python dependencies
├── docker-compose.yml           ← Full stack (Ollama + Qdrant + Agent)
│
├── config/
│   └── node_config.yaml
│
├── identity/
│   ├── identity.py             ← Ed25519 key generation
│   └── wallet.py               ← Polygon wallet generation
│
├── services/                   ← Core services
│   ├── llm_service.py          ← Ollama wrapper
│   ├── telegram_service.py      ← Telegram bot
│   └── email_service.py         ← SMTP email
│
├── memory/                     ← AI Obsidian Memory
│   ├── database.py             ← SQLite layer
│   ├── qdrant_client.py        ← Vector storage
│   └── obsidian_layer.py       ← Intelligent memory
│
├── agent/                      ← LangGraph agents
│   ├── marketing_graph.py      ← Information collection
│   ├── decision_graph.py        ← Owner authority
│   └── network_graph.py        ← Associate network
│
├── graphs/                     ← Additional graphs
│   ├── rag_query_graph.py       ← RAG query pipeline
│   ├── router_graph.py          ← Multi-bot routing
│   └── sync_graph.py            ← Network sync
│
├── core/
│   ├── badge.py
│   └── verification.py
│
├── bots/
│   └── launcher.py
│
├── docker/
│   └── bot/
│       ├── Dockerfile
│       └── run_bot.py
│
├── registry/                   ← Off-chain registry
│   └── ...
│
├── contracts/                  ← Smart contracts
│   └── ...
│
└── tests/
    └── ...
```

---

## Key Features

### 1. AI-Powered Registration Flow

```
User: "Register my textile export business"
  ↓
LLM Intent Parser (Ollama) → Extract Business Name
  ↓
Validate Identity
  ↓
Check Existing (SQLite) + Semantic Duplicate (Qdrant)
  ↓
AI Decision Node (LLM reasoning)
  ↓
Store + Embed + Link → Activate Node
```

### 2. Autonomous Agent Levels

| Level | Behavior |
|-------|----------|
| **Level 1** | Assistive - AI suggests, owner approves |
| **Level 2** | Semi-autonomous - Low-risk actions auto-executed |
| **Level 3** | Fully autonomous - AI negotiates, interacts |

### 3. RAG Query Flow

```
User query → Embed → Qdrant search → Context → LLM → Response
```

### 4. Associate Network

AI can identify opportunities and connect leads with:
- Pre-registered associates
- Role-based matching
- Telegram + Email outreach

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `OWNER_TELEGRAM_ID` | Yes | Your Telegram ID |
| `LLM_MODEL` | No | LLM model (default: qwen2.5) |
| `EMBEDDING_MODEL` | No | Embedding model (default: nomic-embed-text) |
| `QDRANT_HOST` | No | Qdrant host (default: localhost) |
| `SMTP_HOST` | No | Email SMTP server |
| `SMTP_USER` | No | SMTP username |
| `SMTP_PASSWORD` | No | SMTP password |
| `AGENT_EMAIL` | No | AI agent email address |

---

## Usage Examples

### Register a Business

```python
from memory.obsidian_layer import register_business_with_memory

result = register_business_with_memory(
    business_name="ABC Textiles",
    owner_telegram_id="123456789",
    owner_email="owner@abctextiles.com"
)
print(result)
```

### Query Memory

```python
from graphs.rag_query_graph import run_rag_query

result = run_rag_query("Show marketing strategies for textile exports")
print(result["response"])
```

### Process a Lead

```python
from agent.marketing_graph import run_marketing_graph

result = run_marketing_graph(
    raw_input="Hi, I'm interested in your services. John from ABC Corp. john@abc.com",
    user_id="123456789"
)
```

### Propose an Action (with owner approval)

```python
from agent.decision_graph import propose_and_execute

result = propose_and_execute(
    action_type="send_intro_email",
    data={"to": "partner@example.com"}
)
```

### Find Network Partners

```python
from agent.network_graph import run_network_graph

result = run_network_graph(lead_data={
    "name": "John",
    "business": "Logistics Co",
    "contact_info": "john@logistics.com"
})
```

---

## Security Notes

- **Never commit `.env`** - it is gitignored
- **Never commit `identity/node_private.pem`** - it is gitignored
- Use strong, unique passwords per node
- Agent email should be a dedicated address

---

## What's Included

✅ AI Obsidian Memory Engine  
✅ LangGraph Workflow Orchestration  
✅ Ollama (Qwen2.5) Integration  
✅ Qdrant Vector Storage  
✅ SQLite Database  
✅ Telegram Bot Interface  
✅ Email Notifications  
✅ Associate Network Graph  
✅ Multi-Bot Router  
✅ Owner Authority System  
✅ Risk-based Autonomy Levels  
✅ Docker Compose Setup  

---

## Roadmap

- [x] Phase 1: Core identity + Docker stack + Telegram bot
- [x] Phase 2: Config management + wallet + Qdrant RAG + tests
- [x] Phase 3: Smart contract + FastAPI registry + event listener + DNS
- [x] Phase 4: AI Obsidian Memory Engine + LangGraph + Autonomous Agents
- [ ] Phase 5: Premium features (Wallet signing, blockchain registry, federated memory)

---

## ⚖ Legal Notice

BizNode is developed by 1BZ DZIT DAO LLC as open-source infrastructure software.

Each deployed node operates independently under the responsibility of its deploying user with strict adherence to international laws and local laws.1bznetwork operates through https://1bz.biz using blockchain technology with registered nodes sharing their resources using dzit tokens as proof of service. 1BZ DZIT DAO LLC is not liable for the act of nodes and each user should be aware of agent act based on program workflow submitted and blockchain opted using smart contracts. 

1BZ DZIT DAO LLC  
A limited liability company organized under the laws of the State of Wyoming, United States.

## Geographic Restrictions

While the BizNode software may be accessed globally as open-source infrastructure, certain programs and network participation models may be restricted by jurisdiction.

The "Registered Node Operator" program, verification services, and future blockchain-integrated features are NOT offered to:

- United States persons
- U.S.-incorporated entities
- Individuals or entities located within the United States
- Persons subject to U.S. regulatory oversight in connection with digital asset activities

## No Solicitation in the United States

Nothing in this repository, website, or associated materials constitutes:

- An offer of securities
- An investment product
- A financial service
- A managed business service
- A digital asset offering

to any U.S. person.

## Independent Deployment

Users located within the United States may independently deploy the open-source software under the Apache 2.0 license.

However, such deployment does NOT constitute participation in any registered node operator program or network governance model.

## Compliance Responsibility

Each user is solely responsible for ensuring compliance with:

- Their local jurisdiction
- Applicable financial regulations
- Export controls
- AI usage laws
- Business operation laws

1BZ DZIT DAO LLC does not verify or monitor user jurisdiction.

## Restricted Jurisdictions

Participation in the Registered Node Operator program is not available to U.S. persons or U.S.-based entities.

By participating in any network registration, the user represents and warrants that they are not:

- A U.S. citizen or resident
- A U.S.-incorporated entity
- Acting on behalf of a U.S. person
