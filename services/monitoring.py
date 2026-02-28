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

Monitoring Service
=================
System observability endpoints for BizNode.
Provides health checks, metrics, and status information.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class MonitoringService:
    """
    Monitoring and observability service for BizNode.
    
    Provides:
    - Health checks
    - System metrics
    - Active task status
    - Scheduler job status
    - Memory size info
    - Qdrant health
    """
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        """
        Initialize monitoring service.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of BizNode.
        
        Returns:
            Health status dictionary
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check database
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            health["components"]["database"] = "healthy"
        except Exception as e:
            health["components"]["database"] = f"unhealthy: {str(e)}"
            health["status"] = "degraded"
        
        # Check Qdrant
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", "6333"))
            )
            client.get_collections()
            health["components"]["qdrant"] = "healthy"
        except Exception as e:
            health["components"]["qdrant"] = f"unavailable: {str(e)}"
            health["status"] = "degraded"
        
        # Check Ollama
        try:
            import requests
            response = requests.get(
                f"{os.getenv('OLLAMA_URL', 'http://localhost:11434')}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                health["components"]["ollama"] = "healthy"
            else:
                health["components"]["ollama"] = "degraded"
        except Exception as e:
            health["components"]["ollama"] = f"unavailable: {str(e)}"
        
        return health
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system metrics.
        
        Returns:
            Metrics dictionary
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Database stats
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Count tasks
            cursor.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
            task_counts = {row[0]: row[1] for row in cursor.fetchall()}
            metrics["tasks"] = task_counts
            
            # Count audit logs
            cursor.execute("SELECT COUNT(*) FROM audit_logs")
            metrics["audit_logs"] = cursor.fetchone()[0]
            
            # Count tool executions
            cursor.execute("SELECT COUNT(*) FROM tool_logs")
            metrics["tool_executions"] = cursor.fetchone()[0]
            
            # Recent failures
            cursor.execute("""
                SELECT COUNT(*) FROM tool_logs 
                WHERE success = 0 
                AND created_at > datetime('now', '-1 hour')
            """)
            metrics["recent_failures"] = cursor.fetchone()[0]
            
            conn.close()
        except Exception as e:
            metrics["error"] = str(e)
        
        # Database file size
        try:
            if os.path.exists(self.db_path):
                metrics["db_size_bytes"] = os.path.getsize(self.db_path)
        except:
            pass
        
        return metrics
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get currently active tasks.
        
        Returns:
            List of active task dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_id, goal, status, created_at, started_at
                FROM tasks
                WHERE status IN ('pending', 'running')
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_failed_tasks(
        self,
        hours: int = 24,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recently failed tasks.
        
        Args:
            hours: Look back period in hours
            limit: Maximum number of tasks to return
            
        Returns:
            List of failed task dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT id, user_id, goal, status, error_message, created_at
                FROM tasks
                WHERE status = 'failed'
                AND created_at > datetime('now', '-{hours} hours')
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get scheduler job status.
        
        Returns:
            Scheduler status dictionary
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get scheduled jobs
            cursor.execute("""
                SELECT id, task_name, enabled, next_run, last_run, status
                FROM scheduled_tasks
                ORDER BY next_run
            """)
            
            scheduled = [dict(row) for row in cursor.fetchall()]
            
            # Get recent job runs
            cursor.execute("""
                SELECT id, scheduled_task_id, status, started_at, completed_at
                FROM scheduled_task_runs
                ORDER BY started_at DESC
                LIMIT 20
            """)
            
            recent_runs = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "scheduled_jobs": scheduled,
                "recent_runs": recent_runs,
                "active_count": len([j for j in scheduled if j.get("enabled")])
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.
        
        Returns:
            Memory statistics dictionary
        """
        stats = {
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # SQLite stats
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Table row counts
            tables = ["tasks", "task_steps", "tool_logs", "audit_logs", "agent_memory_index"]
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                except:
                    pass
            
            conn.close()
        except Exception as e:
            stats["error"] = str(e)
        
        # Qdrant stats
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", "6333"))
            )
            
            collections = client.get_collections()
            stats["qdrant_collections"] = len(collections.collections)
            
            # Get collection info
            collection_info = {}
            for col in collections.collections:
                try:
                    info = client.get_collection(col.name)
                    collection_info[col.name] = {
                        "vectors_count": info.vectors_count,
                        "points_count": info.points_count
                    }
                except:
                    pass
            
            stats["qdrant_collections_info"] = collection_info
            
        except Exception as e:
            stats["qdrant_error"] = str(e)
        
        return stats
    
    def get_recent_audit_events(
        self,
        event_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit events.
        
        Args:
            event_types: Optional list of event types to filter
            limit: Maximum number of events
            
        Returns:
            List of audit event dictionaries
        """
        try:
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
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_full_status(self) -> Dict[str, Any]:
        """
        Get full system status.
        
        Returns:
            Complete status dictionary
        """
        return {
            "health": self.get_health_status(),
            "metrics": self.get_system_metrics(),
            "active_tasks": self.get_active_tasks(),
            "failed_tasks": self.get_failed_tasks(),
            "scheduler": self.get_scheduler_status(),
            "memory": self.get_memory_stats()
        }


# Global instance
_monitoring_service = None


def get_monitoring_service(db_path: str = "memory/biznode.db") -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service
    
    if _monitoring_service is None:
        _monitoring_service = MonitoringService(db_path)
    
    return _monitoring_service


if __name__ == "__main__":
    # Test the monitoring service
    service = get_monitoring_service()
    
    print("Health Check:")
    print(json.dumps(service.get_health_status(), indent=2))
    
    print("\nMetrics:")
    print(json.dumps(service.get_system_metrics(), indent=2))
