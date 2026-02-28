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

Agent Loop
=========
Main autonomous agent loop that plans, executes, and learns from tasks.
"""

import uuid
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from automation.planner import Planner
from automation.executor import Executor
from automation.schemas import TaskStatus


class AgentLoop:
    """
    Main autonomous agent loop.
    
    Handles:
    - Goal interpretation
    - Planning
    - Execution
    - Evaluation
    - Learning
    """
    
    def __init__(
        self,
        db_path: str = "memory/biznode.db",
        planner: Optional[Planner] = None,
        executor: Optional[Executor] = None,
        max_retries: int = 3,
        on_step_complete: Optional[Callable] = None,
        on_task_complete: Optional[Callable] = None
    ):
        """
        Initialize the agent loop.
        
        Args:
            db_path: Path to SQLite database
            planner: Optional planner instance
            executor: Optional executor instance
            max_retries: Maximum retry attempts per step
            on_step_complete: Callback for step completion
            on_task_complete: Callback for task completion
        """
        self.db_path = db_path
        self.planner = planner or Planner()
        self.executor = executor or Executor()
        self.max_retries = max_retries
        self.on_step_complete = on_step_complete
        self.on_task_complete = on_task_complete
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with automation tables."""
        from automation.schemas import create_automation_tables
        create_automation_tables(self.db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_task(
        self,
        user_id: str,
        goal: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        Create a new task.
        
        Args:
            user_id: User who initiated the task
            goal: Task goal
            context: Optional context
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tasks (id, user_id, goal, status, plan_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            task_id,
            user_id,
            goal,
            TaskStatus.PENDING.value,
            json.dumps(context) if context else None
        ))
        
        conn.commit()
        conn.close()
        
        return task_id
    
    def _update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Update task status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        if status == TaskStatus.RUNNING.value:
            cursor.execute("""
                UPDATE tasks 
                SET status = ?, started_at = ?, updated_at = ?
                WHERE id = ?
            """, (status, now, now, task_id))
        elif status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
            cursor.execute("""
                UPDATE tasks 
                SET status = ?, result_json = ?, error_message = ?, 
                    completed_at = ?, updated_at = ?
                WHERE id = ?
            """, (
                status,
                json.dumps(result) if result else None,
                error,
                now,
                now,
                task_id
            ))
        else:
            cursor.execute("""
                UPDATE tasks 
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, now, task_id))
        
        conn.commit()
        conn.close()
    
    def run(
        self,
        user_id: str,
        goal: str,
        context: Optional[Dict] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Run the agent loop for a goal.
        
        Args:
            user_id: User who initiated the task
            goal: The goal to achieve
            context: Optional context (business data, etc.)
            max_iterations: Maximum replanning iterations
            
        Returns:
            Task result dictionary
        """
        # Create task
        task_id = self._create_task(user_id, goal, context)
        
        # Update status to running
        self._update_task_status(task_id, TaskStatus.RUNNING.value)
        
        try:
            # Step 1: Create plan
            plan = self.planner.create_plan(goal, context)
            
            # Save plan to task
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET plan_json = ? WHERE id = ?
            """, (json.dumps(plan), task_id))
            conn.commit()
            conn.close()
            
            # Step 2: Execute plan
            execution_result = self.executor.execute_plan(task_id, plan)
            
            # Step 3: Evaluate result
            success = execution_result.get("success", False)
            
            if success:
                self._update_task_status(
                    task_id,
                    TaskStatus.COMPLETED.value,
                    result=execution_result
                )
                
                # Store in memory for learning
                self._store_in_memory(task_id, goal, execution_result)
                
                if self.on_task_complete:
                    self.on_task_complete(task_id, execution_result)
                
                return {
                    "task_id": task_id,
                    "success": True,
                    "result": execution_result
                }
            else:
                # Try to recover with replanning
                for iteration in range(max_iterations):
                    # Get failed step info
                    failed_step = None
                    for step_result in execution_result.get("results", []):
                        if not step_result["result"]["success"]:
                            failed_step = step_result
                            break
                    
                    if failed_step:
                        error_msg = failed_step["result"].get("error", "Unknown error")
                        
                        # Create recovery plan
                        recovery_goal = f"Failed to: {goal}. Error: {error_msg}. How to fix this?"
                        recovery_plan = self.planner.create_plan(
                            recovery_goal,
                            {"original_goal": goal, "error": error_msg}
                        )
                        
                        # Execute recovery plan
                        recovery_result = self.executor.execute_plan(
                            f"{task_id}-retry-{iteration}",
                            recovery_plan
                        )
                        
                        if recovery_result.get("success"):
                            self._update_task_status(
                                task_id,
                                TaskStatus.COMPLETED.value,
                                result={
                                    "original_result": execution_result,
                                    "recovery_result": recovery_result
                                }
                            )
                            
                            return {
                                "task_id": task_id,
                                "success": True,
                                "recovered": True,
                                "result": recovery_result
                            }
                
                # Failed after all retries
                self._update_task_status(
                    task_id,
                    TaskStatus.FAILED.value,
                    error="Failed after max retries"
                )
                
                return {
                    "task_id": task_id,
                    "success": False,
                    "error": "Failed after max retries",
                    "result": execution_result
                }
                
        except Exception as e:
            self._update_task_status(
                task_id,
                TaskStatus.FAILED.value,
                error=str(e)
            )
            
            return {
                "task_id": task_id,
                "success": False,
                "error": str(e)
            }
    
    def _store_in_memory(self, task_id: str, goal: str, result: Dict):
        """Store task outcome in memory for learning."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Determine importance based on result
            importance = 0.8 if result.get("success") else 0.3
            
            cursor.execute("""
                INSERT INTO agent_memory_index 
                (id, task_id, content, memory_type, importance_score)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                task_id,
                f"Goal: {goal}\nResult: {json.dumps(result)}",
                "task_outcome",
                importance
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Warning: Failed to store in memory: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_task_steps(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all steps for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM task_steps 
            WHERE task_id = ? 
            ORDER BY step_order
        """, (task_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def list_tasks(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filters."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks"
        params = []
        
        if user_id or status:
            conditions = []
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        self._update_task_status(task_id, TaskStatus.CANCELLED.value)
        return True


# Convenience function
def run_agent_goal(
    user_id: str,
    goal: str,
    context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Run an autonomous goal.
    
    Args:
        user_id: User ID
        goal: Goal to achieve
        context: Optional context
        
    Returns:
        Result dictionary
    """
    agent = AgentLoop()
    return agent.run(user_id, goal, context)


if __name__ == "__main__":
    # Test the agent
    agent = AgentLoop()
    
    # Run a test goal
    result = agent.run(
        user_id="test_user",
        goal="Check the time and send it to the owner",
        context={"owner_id": "12345"}
    )
    
    print(json.dumps(result, indent=2))
