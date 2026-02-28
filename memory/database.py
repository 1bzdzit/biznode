"""
BizNode SQLite Database Layer
============================
Handles structured state and business metadata storage.
Tables: notes, note_links, leads, owner_actions, associates, agent_identity, businesses

This is part of the AI Obsidian Memory Layer.
"""

import sqlite3
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Database path — use absolute path derived from project root to avoid CWD issues
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("SQLITE_PATH", os.path.join(_PROJECT_ROOT, "memory", "biznode.db"))


def get_connection():
    """Get SQLite database connection with WAL mode enabled."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
    
    return conn


def init_db():
    """Initialize database with all required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # === AI Obsidian Memory Tables ===
    
    # Notes table - stores business notes with summaries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT,
            title TEXT,
            content TEXT,
            summary TEXT,
            tags TEXT,
            embedding_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Note links - for semantic backlinking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS note_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            target_id INTEGER,
            similarity REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES notes(id),
            FOREIGN KEY (target_id) REFERENCES notes(id)
        )
    """)
    
    # === Business Registration Tables ===
    
    # Businesses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT UNIQUE,
            business_name TEXT,
            owner_telegram_id TEXT,
            owner_email TEXT,
            status TEXT DEFAULT 'active',
            wallet_address TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # === Lead Management Tables ===
    
    # Leads table - for marketing mode
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            business TEXT,
            contact_info TEXT,
            summary TEXT,
            source TEXT,
            status TEXT DEFAULT 'new',
            embedding_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # === Owner Authority Tables ===
    
    # Owner actions - tracks owner approvals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owner_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            data TEXT,
            status TEXT DEFAULT 'pending',
            owner_response TEXT,
            risk_level TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME
        )
    """)
    
    # === 1bz Associate Network Tables ===
    
    # Associates table - pre-registered network partners
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS associates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id TEXT UNIQUE,
            name TEXT,
            telegram_id TEXT,
            email TEXT,
            role TEXT,
            business_type TEXT,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Network interactions - logs associate communications
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS network_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            associate_id INTEGER,
            interaction_type TEXT,
            description TEXT,
            initiated_by TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (associate_id) REFERENCES associates(id)
        )
    """)
    
    # === Agent Identity Table ===
    
    # AI Agent identity configuration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_identity (
            id INTEGER PRIMARY KEY,
            agent_name TEXT,
            agent_email TEXT,
            telegram_bot_token TEXT,
            smtp_host TEXT,
            smtp_port INTEGER,
            smtp_user TEXT,
            smtp_password TEXT,
            owner_telegram_id TEXT,
            owner_email TEXT,
            autonomy_level INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # === 1bz Network Sync Table ===
    
    # Sync registry for decentralized tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT,
            hash_data TEXT,
            signature TEXT,
            sync_status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            synced_at DATETIME
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")


# === Notes CRUD ===

def create_note(node_id: str, title: str, content: str, summary: str = "", tags: str = "") -> int:
    """Create a new note."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notes (node_id, title, content, summary, tags) VALUES (?, ?, ?, ?, ?)",
        (node_id, title, content, summary, tags)
    )
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_note(note_id: int) -> Optional[Dict]:
    """Get note by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_notes() -> List[Dict]:
    """Get all notes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_note(note_id: int, **kwargs) -> bool:
    """Update note fields."""
    conn = get_connection()
    cursor = conn.cursor()
    fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [note_id]
    cursor.execute(f"UPDATE notes SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def delete_note(note_id: int) -> bool:
    """Delete a note."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


# === Note Links CRUD ===

def create_link(source_id: int, target_id: int, similarity: float) -> int:
    """Create a link between notes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO note_links (source_id, target_id, similarity) VALUES (?, ?, ?)",
        (source_id, target_id, similarity)
    )
    link_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return link_id


def get_links_for_note(note_id: int) -> List[Dict]:
    """Get all links for a note."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nl.*, n.title, n.summary 
        FROM note_links nl
        JOIN notes n ON nl.target_id = n.id
        WHERE nl.source_id = ? OR nl.target_id = ?
    """, (note_id, note_id))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# === Business CRUD ===

def create_business(node_id: str, business_name: str, owner_telegram_id: str, 
                    owner_email: str = "", wallet_address: str = "") -> int:
    """Register a new business."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO businesses (node_id, business_name, owner_telegram_id, 
           owner_email, wallet_address) VALUES (?, ?, ?, ?, ?)""",
        (node_id, business_name, owner_telegram_id, owner_email, wallet_address)
    )
    business_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return business_id


def get_business(node_id: str) -> Optional[Dict]:
    """Get business by node_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM businesses WHERE node_id = ?", (node_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_businesses() -> List[Dict]:
    """Get all businesses."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM businesses ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def check_business_exists(business_name: str) -> Optional[Dict]:
    """Check if business already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM businesses WHERE business_name = ? COLLATE NOCASE",
        (business_name,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# === Lead Management ===

def create_lead(name: str, business: str, contact_info: str, 
                summary: str = "", source: str = "telegram") -> int:
    """Create a new lead."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO leads (name, business, contact_info, summary, source) 
           VALUES (?, ?, ?, ?, ?)""",
        (name, business, contact_info, summary, source)
    )
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id


def get_lead(lead_id: int) -> Optional[Dict]:
    """Get lead by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_leads(status: str = None) -> List[Dict]:
    """Get all leads, optionally filtered by status."""
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM leads WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_lead_status(lead_id: int, status: str) -> bool:
    """Update lead status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


# === Owner Actions ===

def create_action(action_type: str, data: Dict, risk_level: str = "low") -> int:
    """Create a new owner action request."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO owner_actions (action_type, data, risk_level) 
           VALUES (?, ?, ?)""",
        (action_type, json.dumps(data), risk_level)
    )
    action_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return action_id


def get_pending_actions() -> List[Dict]:
    """Get all pending owner actions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM owner_actions WHERE status = 'pending' ORDER BY created_at"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def resolve_action(action_id: int, response: str) -> bool:
    """Resolve an owner action (approve/reject)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE owner_actions 
           SET status = ?, owner_response = ?, resolved_at = CURRENT_TIMESTAMP 
           WHERE id = ?""",
        ("resolved", response, action_id)
    )
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


# === Associates ===

def create_associate(network_id: str, name: str, telegram_id: str, 
                    email: str, role: str, business_type: str = "") -> int:
    """Register a new associate."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO associates (network_id, name, telegram_id, email, role, business_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (network_id, name, telegram_id, email, role, business_type)
    )
    associate_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return associate_id


def get_associate(associate_id: int) -> Optional[Dict]:
    """Get associate by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM associates WHERE id = ?", (associate_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_associates_by_role(role: str) -> List[Dict]:
    """Get all associates with a specific role."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM associates WHERE role = ? AND status = 'active'",
        (role,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_associates() -> List[Dict]:
    """Get all active associates."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM associates WHERE status = 'active'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_network_interaction(associate_id: int, interaction_type: str, 
                            description: str, initiated_by: str) -> int:
    """Log an interaction with an associate."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO network_interactions 
           (associate_id, interaction_type, description, initiated_by)
           VALUES (?, ?, ?, ?)""",
        (associate_id, interaction_type, description, initiated_by)
    )
    interaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return interaction_id


# === Agent Identity ===

def save_agent_identity(identity: Dict) -> bool:
    """Save or update agent identity."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM agent_identity WHERE id = 1")
    exists = cursor.fetchone()
    
    if exists:
        cursor.execute("""
            UPDATE agent_identity SET
                agent_name = ?, agent_email = ?, telegram_bot_token = ?,
                smtp_host = ?, smtp_port = ?, smtp_user = ?, smtp_password = ?,
                owner_telegram_id = ?, owner_email = ?, autonomy_level = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (
            identity.get('agent_name'), identity.get('agent_email'),
            identity.get('telegram_bot_token'), identity.get('smtp_host'),
            identity.get('smtp_port'), identity.get('smtp_user'),
            identity.get('smtp_password'), identity.get('owner_telegram_id'),
            identity.get('owner_email'), identity.get('autonomy_level', 1)
        ))
    else:
        cursor.execute("""
            INSERT INTO agent_identity VALUES (
                1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """, (
            identity.get('agent_name'), identity.get('agent_email'),
            identity.get('telegram_bot_token'), identity.get('smtp_host'),
            identity.get('smtp_port'), identity.get('smtp_user'),
            identity.get('smtp_password'), identity.get('owner_telegram_id'),
            identity.get('owner_email'), identity.get('autonomy_level', 1)
        ))
    
    conn.commit()
    conn.close()
    return True


def get_agent_identity() -> Optional[Dict]:
    """Get agent identity."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_identity WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# === Sync Registry ===

def create_sync_record(node_id: str, hash_data: str, signature: str = "") -> int:
    """Create a sync record for 1bz network."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sync_registry (node_id, hash_data, signature) VALUES (?, ?, ?)",
        (node_id, hash_data, signature)
    )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_pending_syncs() -> List[Dict]:
    """Get all pending sync records."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sync_registry WHERE sync_status = 'pending'"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_synced(record_id: int) -> bool:
    """Mark a sync record as synced."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE sync_registry 
           SET sync_status = 'synced', synced_at = CURRENT_TIMESTAMP 
           WHERE id = ?""",
        (record_id,)
    )
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


# === Utility Functions ===

def search_businesses(query: str) -> List[Dict]:
    """Search businesses by name."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM businesses WHERE business_name LIKE ?",
        (f"%{query}%",)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()
    print("Database setup complete.")
