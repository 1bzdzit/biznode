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

Background Worker / Scheduler
============================
Background worker for running scheduled and recurring tasks.
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional


class BackgroundScheduler:
    """
    Background scheduler for running recurring tasks.
    
    Features:
    - Interval-based scheduling
    - Cron-like scheduling (basic)
    - One-time scheduled tasks
    - Task queue for async execution
    """
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        """
        Initialize the scheduler.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._running = False
        self._thread = None
        self._check_interval = 60  # Check every 60 seconds
        
        # Ensure tables exist
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure scheduler tables exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                task_type TEXT,
                cron_expression TEXT,
                interval_seconds INTEGER,
                action_json TEXT NOT NULL,
               1,
                last enabled INTEGER DEFAULT _run TEXT,
                next_run TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def start(self):
        """Start the background scheduler."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("Background scheduler started.")
    
    def stop(self):
        """Stop the background scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("Background scheduler stopped.")
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                self._check_and_run_tasks()
            except Exception as e:
                print(f"Scheduler error: {e}")
            
            time.sleep(self._check_interval)
    
    def _check_and_run_tasks(self):
        """Check for due tasks and run them."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        # Find due tasks
        cursor.execute("""
            SELECT * FROM scheduled_tasks
            WHERE enabled = 1
            AND status = 'active'
            AND next_run IS NOT NULL
            AND next_run <= ?
        """, (now,))
        
        due_tasks = cursor.fetchall()
        
        for task in due_tasks:
            self._run_scheduled_task(dict(task))
        
        conn.close()
    
    def _run_scheduled_task(self, task: Dict):
        """Run a scheduled task."""
        import uuid
        
        task_id = task.get("id")
        task_name = task.get("task_name")
        action_json = task.get("action_json")
        
        print(f"Running scheduled task: {task_name}")
        
        # Create a run record
        run_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scheduled_task_runs (id, scheduled_task_id, status)
            VALUES (?, ?, 'running')
        """, (run_id, task_id))
        
        conn.commit()
        
        try:
            # Parse action and execute
            action = json.loads(action_json)
            
            # Execute based on action type
            result = self._execute_action(action)
            
            # Update run record
            cursor.execute("""
                UPDATE scheduled_task_runs
                SET status = 'completed', completed_at = ?, result_json = ?
                WHERE id = ?
            """, (
                datetime.utcnow().isoformat(),
                json.dumps(result),
                run_id
            ))
            
            # Update task last_run and next_run
            self._update_task_schedule(task_id, cursor)
            
            conn.commit()
            
        except Exception as e:
            # Mark run as failed
            cursor.execute("""
                UPDATE scheduled_task_runs
                SET status = 'failed', completed_at = ?, error_message = ?
                WHERE id = ?
            """, (
                datetime.utcnow().isoformat(),
                str(e),
                run_id
            ))
            conn.commit()
        
        conn.close()
    
    def _execute_action(self, action: Dict) -> Dict:
        """Execute a scheduled action."""
        action_type = action.get("type", "agent_goal")
        
        if action_type == "agent_goal":
            from automation.agent_loop import run_agent_goal
            
            goal = action.get("goal", "")
            context = action.get("context", {})
            
            result = run_agent_goal(
                user_id=action.get("user_id", "scheduler"),
                goal=goal,
                context=context
            )
            
            return result
        
        elif action_type == "tool":
            from automation.registry import get_tool
            
            tool_name = action.get("tool")
            tool_args = action.get("arguments", {})
            
            tool = get_tool(tool_name)
            result = tool.run(**tool_args)
            
            return result
        
        elif action_type == "webhook":
            from tools.webhook_tool import WebhookTool
            
            url = action.get("url")
            method = action.get("method", "POST")
            data = action.get("data", {})
            
            tool = WebhookTool()
            return tool.run(url=url, method=method, data=data)
        
        else:
            return {"error": f"Unknown action type: {action_type}"}
    
    def _update_task_schedule(self, task_id: str, cursor):
        """Update task schedule after execution."""
        cursor.execute("""
            SELECT interval_seconds FROM scheduled_tasks WHERE id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        
        if row and row["interval_seconds"]:
            interval = row["interval_seconds"]
            next_run = datetime.utcnow() + timedelta(seconds=interval)
            
            cursor.execute("""
                UPDATE scheduled_tasks
                SET last_run = ?, next_run = ?
                WHERE id = ?
            """, (
                datetime.utcnow().isoformat(),
                next_run.isoformat(),
                task_id
            ))
    
    def schedule_interval(
        self,
        task_name: str,
        interval_seconds: int,
        action: Dict,
        user_id: str = "system"
    ) -> str:
        """
        Schedule a task to run at intervals.
        
        Args:
            task_name: Name of the task
            interval_seconds: Interval in seconds
            action: Action to execute
            user_id: User who scheduled the task
            
        Returns:
            Task ID
        """
        import uuid
        
        task_id = str(uuid.uuid4())
        next_run = datetime.utcnow() + timedelta(seconds=interval_seconds)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scheduled_tasks 
            (id, task_name, task_type, interval_seconds, action_json, next_run, created_by)
            VALUES (?, ?, 'interval', ?, ?, ?, ?)
        """, (
            task_id,
            task_name,
            interval_seconds,
            json.dumps(action),
            next_run.isoformat(),
            user_id
        ))
        
        conn.commit()
        conn.close()
        
        return task_id
    
    def schedule_once(
        self,
        task_name: str,
        run_at: datetime,
        action: Dict,
        user_id: str = "system"
    ) -> str:
        """
        Schedule a one-time task.
        
        Args:
            task_name: Name of the task
            run_at: When to run
            action: Action to execute
            user_id: User who scheduled the task
            
        Returns:
            Task ID
        """
        import uuid
        
        task_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scheduled_tasks 
            (id, task_name, task_type, action_json, next_run, created_by)
            VALUES (?, ?, 'once', ?, ?, ?)
        """, (
            task_id,
            task_name,
            json.dumps(action),
            run_at.isoformat(),
            user_id
        ))
        
        conn.commit()
        conn.close()
        
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE scheduled_tasks SET enabled = 0, status = 'cancelled'
            WHERE id = ?
        """, (task_id,))
        
        conn.commit()
        conn.close()
        
        return True
    
    def list_tasks(
        self,
        enabled_only: bool = False
    ) -> List[Dict]:
        """List scheduled tasks."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if enabled_only:
            cursor.execute("""
                SELECT * FROM scheduled_tasks 
                WHERE enabled = 1
                ORDER BY next_run
            """)
        else:
            cursor.execute("""
                SELECT * FROM scheduled_tasks
                ORDER BY created_at DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


# Global scheduler instance
_scheduler = None


def get_scheduler(db_path: str = "memory/biznode.db") -> BackgroundScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler(db_path)
    
    return _scheduler


def start_scheduler(db_path: str = "memory/biznode.db"):
    """Start the global scheduler."""
    scheduler = get_scheduler(db_path)
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler
    
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


if __name__ == "__main__":
    # Test the scheduler
    scheduler = BackgroundScheduler()
    
    # Schedule a simple task
    scheduler.schedule_interval(
        task_name="test_task",
        interval_seconds=60,
        action={
            "type": "agent_goal",
            "goal": "Check system status",
            "user_id": "test"
        }
    )
    
    # Start scheduler
    scheduler.start()
    
    # Run for a bit
    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
