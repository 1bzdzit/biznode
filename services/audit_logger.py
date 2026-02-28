"""
BizNode – Digital Business Operator
Copyright 2026 1BZ DZIT DAO LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

---

Audit Logger Service
==================
Enterprise-grade audit logging for all autonomous actions.
Provides signed audit trails for legal compliance and forensic analysis.
"""

import json
import uuid
import hashlib
import sqlite3
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import wraps


class AuditLogger:
    """
    Enterprise audit logger with cryptographic signing.
    
    All autonomous actions are logged with:
    - Unique event ID
    - Timestamp
    - Event type
    - Payload (JSON)
    - Autonomy level
    - User context
    - Cryptographic signature (future: for blockchain anchoring)
    """
    
    EVENT_TYPES = [
        "PLAN_CREATED",
        "PLAN_VALIDATED",
        "TOOL_EXECUTE",
        "TOOL_SUCCESS",
        "TOOL_FAILURE",
        "EVALUATE",
        "APPROVAL_REQUEST",
        "APPROVAL_GRANTED",
        "APPROVAL_DENIED",
        "TASK_STARTED",
        "TASK_COMPLETED",
        "TASK_FAILED",
        "TASK_CANCELLED",
        "SCHEDULE_CREATED",
        "SCHEDULE_TRIGGERED",
        "SCHEDULE_COMPLETED",
        "MEMORY_STORED",
        "DECISION_MADE",
        "ERROR_OCCURRED",
        "USER_ACTION"
    ]
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        """
        Initialize the audit logger.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_table()
        self._node_id = None
    
    def _ensure_table(self):
        """Ensure audit_logs table exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                event_type TEXT NOT NULL,
                payload TEXT,
                autonomy_level INTEGER,
                user_id TEXT,
                tool_name TEXT,
                signature TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit_logs(task_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at)
        """)
        
        conn.commit()
        conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn
    
    def _generate_signature(self, data: str) -> str:
        """
        Generate a cryptographic signature for the audit entry.
        
        Note: For blockchain anchoring, this would use the node's Ed25519 key.
        For now, we use HMAC-SHA256.
        """
        # In production, use the node's private key
        # For now, use a derived key from environment
        secret = os.getenv("NODE_SIGNING_KEY", "biznode-audit-secret")
        
        signature = hashlib.sha256(
            f"{data}{secret}".encode()
        ).hexdigest()
        
        return signature
    
    def _create_entry(
        self,
        event_type: str,
        payload: Optional[Dict] = None,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        autonomy_level: Optional[int] = None,
        tool_name: Optional[str] = None
    ) -> str:
        """Create an audit log entry."""
        entry_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        payload_json = json.dumps(payload) if payload else None
        
        # Generate signature
        signature_data = f"{entry_id}:{event_type}:{payload_json}:{datetime.utcnow().isoformat()}"
        signature = self._generate_signature(signature_data)
        
        cursor.execute("""
            INSERT INTO audit_logs 
            (id, task_id, event_type, payload, autonomy_level, user_id, tool_name, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            task_id,
            event_type,
            payload_json,
            autonomy_level,
            user_id,
            tool_name,
            signature
        ))
        
        conn.commit()
        conn.close()
        
        return entry_id
    
    # High-level logging methods
    
    def log_plan_created(
        self,
        task_id: str,
        plan: Dict[str, Any],
        user_id: Optional[str] = None,
        autonomy_level: Optional[int] = None
    ) -> str:
        """Log plan creation."""
        return self._create_entry(
            event_type="PLAN_CREATED",
            payload={"plan": plan},
            task_id=task_id,
            user_id=user_id,
            autonomy_level=autonomy_level
        )
    
    def log_tool_execute(
        self,
        task_id: str,
        step_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        autonomy_level: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Log tool execution start."""
        return self._create_entry(
            event_type="TOOL_EXECUTE",
            payload={
                "step_id": step_id,
                "arguments": arguments
            },
            task_id=task_id,
            user_id=user_id,
            autonomy_level=autonomy_level,
            tool_name=tool_name
        )
    
    def log_tool_result(
        self,
        task_id: str,
        step_id: str,
        tool_name: str,
        success: bool,
        result: Any,
        execution_time_ms: int,
        autonomy_level: Optional[int] = None
    ) -> str:
        """Log tool execution result."""
        event_type = "TOOL_SUCCESS" if success else "TOOL_FAILURE"
        
        return self._create_entry(
            event_type=event_type,
            payload={
                "step_id": step_id,
                "result": str(result)[:1000],  # Truncate for storage
                "execution_time_ms": execution_time_ms
            },
            task_id=task_id,
            autonomy_level=autonomy_level,
            tool_name=tool_name
        )
    
    def log_approval_request(
        self,
        task_id: str,
        action_type: str,
        risk_level: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Log approval request."""
        return self._create_entry(
            event_type="APPROVAL_REQUEST",
            payload={
                "action_type": action_type,
                "risk_level": risk_level,
                "details": details
            },
            task_id=task_id,
            user_id=user_id
        )
    
    def log_approval_decision(
        self,
        task_id: str,
        approved: bool,
        approver: str,
        autonomy_level: int
    ) -> str:
        """Log approval decision."""
        event_type = "APPROVAL_GRANTED" if approved else "APPROVAL_DENIED"
        
        return self._create_entry(
            event_type=event_type,
            payload={"approver": approver},
            task_id=task_id,
            autonomy_level=autonomy_level
        )
    
    def log_task_started(
        self,
        task_id: str,
        goal: str,
        user_id: Optional[str] = None,
        autonomy_level: Optional[int] = None
    ) -> str:
        """Log task start."""
        return self._create_entry(
            event_type="TASK_STARTED",
            payload={"goal": goal},
            task_id=task_id,
            user_id=user_id,
            autonomy_level=autonomy_level
        )
    
    def log_task_completed(
        self,
        task_id: str,
        result: Dict[str, Any],
        autonomy_level: Optional[int] = None
    ) -> str:
        """Log task completion."""
        return self._create_entry(
            event_type="TASK_COMPLETED",
            payload={"result": result},
            task_id=task_id,
            autonomy_level=autonomy_level
        )
    
    def log_task_failed(
        self,
        task_id: str,
        error: str,
        autonomy_level: Optional[int] = None
    ) -> str:
        """Log task failure."""
        return self._create_entry(
            event_type="TASK_FAILED",
            payload={"error": error},
            task_id=task_id,
            autonomy_level=autonomy_level
        )
    
    def log_decision(
        self,
        task_id: str,
        decision: str,
        reasoning: str,
        autonomy_level: int
    ) -> str:
        """Log autonomous decision."""
        return self._create_entry(
            event_type="DECISION_MADE",
            payload={
                "decision": decision,
                "reasoning": reasoning
            },
            task_id=task_id,
            autonomy_level=autonomy_level
        )
    
    def log_error(
        self,
        error: str,
        context: Optional[Dict] = None,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Log error occurrence."""
        return self._create_entry(
            event_type="ERROR_OCCURRED",
            payload={
                "error": error,
                "context": context
            },
            task_id=task_id,
            user_id=user_id
        )
    
    # Query methods
    
    def get_task_audit_trail(self, task_id: str) -> List[Dict]:
        """Get complete audit trail for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM audit_logs
            WHERE task_id = ?
            ORDER BY created_at ASC
        """, (task_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get events by type."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM audit_logs
            WHERE event_type = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (event_type, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_recent_events(
        self,
        limit: int = 100,
        event_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get recent events."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if event_types:
            placeholders = ",".join(["?"] * len(event_types))
            cursor.execute(f"""
                SELECT * FROM audit_logs
                WHERE event_type IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT ?
            """, (*event_types, limit))
        else:
            cursor.execute("""
                SELECT * FROM audit_logs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_failed_events(self, limit: int = 50) -> List[Dict]:
        """Get failed events for analysis."""
        return self.get_events_by_type("TOOL_FAILURE", limit)
    
    def get_error_events(self, limit: int = 50) -> List[Dict]:
        """Get error events."""
        return self.get_events_by_type("ERROR_OCCURRED", limit)
    
    def verify_integrity(self, task_id: str) -> Dict[str, Any]:
        """
        Verify the integrity of a task's audit trail.
        
        Returns verification result with signature validation.
        """
        trail = self.get_task_audit_trail(task_id)
        
        if not trail:
            return {
                "valid": False,
                "error": "No audit trail found"
            }
        
        # Verify each signature
        for entry in trail:
            expected_sig = self._generate_signature(
                f"{entry['id']}:{entry['event_type']}:{entry['payload']}:{entry['created_at']}"
            )
            
            if entry['signature'] != expected_sig:
                return {
                    "valid": False,
                    "error": f"Signature mismatch for entry {entry['id']}"
                }
        
        return {
            "valid": True,
            "entries": len(trail),
            "task_id": task_id
        }


# Decorator for automatic audit logging
def audit_log(event_type: str):
    """Decorator for automatic audit logging."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = AuditLogger()
            
            # Extract context from kwargs
            task_id = kwargs.get('task_id')
            user_id = kwargs.get('user_id')
            
            try:
                result = func(*args, **kwargs)
                
                # Log success
                logger._create_entry(
                    event_type=event_type,
                    payload={"args": str(args)[:200], "kwargs": str(kwargs)[:200]},
                    task_id=task_id,
                    user_id=user_id
                )
                
                return result
            except Exception as e:
                # Log error
                logger.log_error(
                    error=str(e),
                    context={"function": func.__name__},
                    task_id=task_id,
                    user_id=user_id
                )
                raise
        
        return wrapper
    return decorator


# Global instance
_audit_logger = None


def get_audit_logger(db_path: str = "memory/biznode.db") -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    
    if _audit_logger is None:
        _audit_logger = AuditLogger(db_path)
    
    return _audit_logger


if __name__ == "__main__":
    # Test the audit logger
    logger = AuditLogger()
    
    # Log a test event
    entry_id = logger.log_task_started(
        task_id="test-task-123",
        goal="Test automation",
        user_id="test_user",
        autonomy_level=2
    )
    
    print(f"Created audit entry: {entry_id}")
    
    # Get audit trail
    trail = logger.get_task_audit_trail("test-task-123")
    print(f"Audit trail: {json.dumps(trail, indent=2)}")
    
    # Verify integrity
    result = logger.verify_integrity("test-task-123")
    print(f"Integrity check: {result}")
