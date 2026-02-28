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

Reminder Tool
============
Tool for creating and managing reminders/tasks.
"""

import uuid
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from tools.base import BaseTool


class ReminderTool(BaseTool):
    """Tool for creating and managing reminders."""
    
    name = "create_reminder"
    description = "Create a reminder or scheduled task"
    category = "scheduler"
    
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Reminder title"
            },
            "description": {
                "type": "string",
                "description": "Reminder description"
            },
            "due_date": {
                "type": "string",
                "description": "Due date (ISO format)"
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "default": "medium"
            },
            "action": {
                "type": "string",
                "description": "Action to perform when triggered"
            }
        },
        "required": ["title"]
    }
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        """Initialize the reminder tool."""
        super().__init__()
        self.db_path = db_path
    
    def run(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: str = "medium",
        action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a reminder.
        
        Args:
            title: Reminder title
            description: Reminder description
            due_date: Due date (ISO format)
            priority: Priority level
            action: Action to perform
            
        Returns:
            Result dictionary
        """
        # Ensure reminders table exists
        self._ensure_table()
        
        reminder_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO reminders 
                (id, title, description, due_date, priority, action, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                reminder_id,
                title,
                description,
                due_date,
                priority,
                action,
                "pending"
            ))
            
            conn.commit()
            
            return {
                "success": True,
                "id": reminder_id,
                "title": title,
                "due_date": due_date
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def _ensure_table(self):
        """Ensure reminders table exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT,
                priority TEXT DEFAULT 'medium',
                action TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def list_reminders(self, status: Optional[str] = None) -> List[Dict]:
        """
        List reminders.
        
        Args:
            status: Filter by status
            
        Returns:
            List of reminders
        """
        self._ensure_table()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM reminders WHERE status = ? ORDER BY due_date",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM reminders ORDER BY due_date")
        
        rows = cursor.fetchall()
        conn.close()
        
        reminders = []
        for row in rows:
            reminders.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "due_date": row[3],
                "priority": row[4],
                "action": row[5],
                "status": row[6],
                "created_at": row[7]
            })
        
        return reminders
    
    def complete_reminder(self, reminder_id: str) -> Dict[str, Any]:
        """Mark a reminder as complete."""
        self._ensure_table()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE reminders 
                SET status = 'completed', completed_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), reminder_id))
            
            conn.commit()
            
            return {
                "success": True,
                "id": reminder_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def get_due_reminders(self) -> List[Dict]:
        """Get reminders that are due."""
        self._ensure_table()
        
        now = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM reminders 
            WHERE status = 'pending' 
            AND due_date IS NOT NULL
            AND due_date <= ?
            ORDER BY due_date
        """, (now,))
        
        rows = cursor.fetchall()
        conn.close()
        
        reminders = []
        for row in rows:
            reminders.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "due_date": row[3],
                "priority": row[4],
                "action": row[5],
                "status": row[6]
            })
        
        return reminders


class ScheduleTaskTool(BaseTool):
    """Tool for scheduling recurring tasks."""
    
    name = "schedule_task"
    description = "Schedule a recurring task"
    category = "scheduler"
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        super().__init__()
        self.db_path = db_path
    
    def run(
        self,
        task_name: str,
        cron_expression: str,
        action: str,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Schedule a recurring task."""
        import uuid
        
        # Ensure table exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                cron_expression TEXT,
                action TEXT,
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                next_run TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        task_id = str(uuid.uuid4())
        
        try:
            cursor.execute("""
                INSERT INTO scheduled_tasks (id, task_name, cron_expression, action, enabled)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, task_name, cron_expression, action, 1 if enabled else 0))
            
            conn.commit()
            
            return {
                "success": True,
                "id": task_id,
                "task_name": task_name,
                "cron_expression": cron_expression
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
