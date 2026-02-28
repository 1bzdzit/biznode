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

Execution Memory Store
=====================
Learning store that records task execution patterns for autonomous improvement.
Tracks success/failure patterns, tool effectiveness, and decision strategies.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict


class ExecutionMemoryStore:
    """
    Execution memory store for learning from task execution.
    
    Records:
    - Tool execution success/failure patterns
    - Task completion patterns
    - Effective tool chains
    - Error patterns and recovery strategies
    - Time-to-completion metrics
    """
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        """
        Initialize execution memory store.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_tables(self):
        """Initialize execution memory tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Execution patterns - tracks tool sequences and outcomes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                tool_sequence TEXT NOT NULL,
                success INTEGER NOT NULL,
                duration_ms INTEGER,
                user_feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tool effectiveness - tracks tool success rates by context
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_effectiveness (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                context_type TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                avg_duration_ms INTEGER,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tool_name, context_type)
            )
        """)
        
        # Error recovery strategies - records how errors were resolved
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_recovery_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                tool_name TEXT,
                recovery_strategy TEXT NOT NULL,
                success_rate REAL DEFAULT 0,
                times_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        """)
        
        # Learned decisions - records decision patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_type TEXT NOT NULL,
                context TEXT,
                chosen_action TEXT NOT NULL,
                alternatives_considered TEXT,
                outcome TEXT NOT NULL,
                reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Task metrics - aggregates task execution metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                autonomy_level INTEGER,
                avg_duration_ms INTEGER,
                success_rate REAL,
                tool_count_avg REAL,
                sample_size INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_type, autonomy_level)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_tool_execution(
        self,
        tool_name: str,
        context_type: str,
        success: bool,
        duration_ms: Optional[int] = None
    ):
        """
        Record a tool execution for learning.
        
        Args:
            tool_name: Name of the tool executed
            context_type: Type of context/task
            success: Whether execution succeeded
            duration_ms: Execution duration in milliseconds
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Update tool effectiveness
        cursor.execute("""
            INSERT INTO tool_effectiveness 
                (tool_name, context_type, success_count, failure_count, avg_duration_ms, last_used)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tool_name, context_type) DO UPDATE SET
                success_count = success_count + CASE WHEN ? THEN 1 ELSE 0 END,
                failure_count = failure_count + CASE WHEN NOT ? THEN 1 ELSE 0 END,
                avg_duration_ms = CASE 
                    WHEN avg_duration_ms IS NULL THEN ?
                    ELSE (avg_duration_ms * sample_size + ?) / (sample_size + 1)
                END,
                last_used = CURRENT_TIMESTAMP
        """, (
            tool_name, context_type, 
            1 if success else 0, 1 if success else 0,
            duration_ms, duration_ms
        ))
        
        conn.commit()
        conn.close()
    
    def record_task_execution(
        self,
        task_type: str,
        tool_sequence: List[str],
        success: bool,
        duration_ms: Optional[int] = None,
        user_feedback: Optional[str] = None
    ):
        """
        Record a task execution pattern.
        
        Args:
            task_type: Type of task executed
            tool_sequence: List of tools used in order
            success: Whether task succeeded
            duration_ms: Total execution time
            user_feedback: Optional user feedback
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Record execution pattern
        cursor.execute("""
            INSERT INTO execution_patterns 
                (task_type, tool_sequence, success, duration_ms, user_feedback)
            VALUES (?, ?, ?, ?, ?)
        """, (
            task_type,
            json.dumps(tool_sequence),
            1 if success else 0,
            duration_ms,
            user_feedback
        ))
        
        # Update task metrics
        cursor.execute("""
            INSERT INTO task_metrics 
                (task_type, avg_duration_ms, success_rate, tool_count_avg, sample_size)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(task_type, autonomy_level) DO UPDATE SET
                avg_duration_ms = CASE 
                    WHEN avg_duration_ms IS NULL THEN ?
                    ELSE (avg_duration_ms * sample_size + ?) / (sample_size + 1)
                END,
                success_rate = CASE 
                    WHEN success_rate IS NULL THEN ?
                    ELSE (success_rate * sample_size + ?) / (sample_size + 1)
                END,
                tool_count_avg = CASE 
                    WHEN tool_count_avg IS NULL THEN ?
                    ELSE (tool_count_avg * sample_size + ?) / (sample_size + 1)
                END,
                sample_size = sample_size + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (
            task_type,
            duration_ms, duration_ms,
            1 if success else 0, 1 if success else 0,
            len(tool_sequence), len(tool_sequence)
        ))
        
        conn.commit()
        conn.close()
    
    def record_error_recovery(
        self,
        error_type: str,
        tool_name: Optional[str],
        recovery_strategy: str,
        success: bool
    ):
        """
        Record an error recovery strategy.
        
        Args:
            error_type: Type of error encountered
            tool_name: Tool that had the error
            recovery_strategy: Strategy used to recover
            success: Whether recovery succeeded
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO error_recovery_strategies 
                (error_type, tool_name, recovery_strategy, success_rate, times_used, last_used)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(error_type, tool_name, recovery_strategy) DO UPDATE SET
                times_used = times_used + 1,
                success_rate = CASE 
                    WHEN success_rate IS NULL THEN ?
                    ELSE (success_rate * times_used + ?) / (times_used + 1)
                END,
                last_used = CURRENT_TIMESTAMP
        """, (
            error_type, tool_name, recovery_strategy,
            1 if success else 0, 1 if success else 0
        ))
        
        conn.commit()
        conn.close()
    
    def record_decision(
        self,
        decision_type: str,
        chosen_action: str,
        outcome: str,
        context: Optional[Dict] = None,
        alternatives: Optional[List[str]] = None,
        reasoning: Optional[str] = None
    ):
        """
        Record a decision for learning.
        
        Args:
            decision_type: Type of decision
            chosen_action: Action that was chosen
            outcome: Outcome of the decision
            context: Context of the decision
            alternatives: Alternative actions considered
            reasoning: Reasoning behind the decision
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO learned_decisions 
                (decision_type, context, chosen_action, alternatives_considered, outcome, reasoning)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            decision_type,
            json.dumps(context) if context else None,
            chosen_action,
            json.dumps(alternatives) if alternatives else None,
            outcome,
            reasoning
        ))
        
        conn.commit()
        conn.close()
    
    def get_effective_tools(
        self,
        context_type: str,
        min_success_rate: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get effective tools for a context type.
        
        Args:
            context_type: Context to get tools for
            min_success_rate: Minimum success rate
            
        Returns:
            List of effective tools sorted by success rate
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tool_name, 
                   CAST(success_count AS REAL) / (success_count + failure_count) as success_rate,
                   avg_duration_ms
            FROM tool_effectiveness
            WHERE context_type = ?
            AND (success_count + failure_count) >= 3
            ORDER BY success_rate DESC, avg_duration_ms ASC
        """, (context_type,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "tool_name": row[0],
                "success_rate": row[1],
                "avg_duration_ms": row[2]
            }
            for row in rows
            if row[1] >= min_success_rate
        ]
    
    def get_successful_patterns(
        self,
        task_type: str,
        min_examples: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get successful execution patterns for a task type.
        
        Args:
            task_type: Type of task
            min_examples: Minimum number of examples
            
        Returns:
            List of successful patterns
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tool_sequence, COUNT(*) as use_count, AVG(duration_ms) as avg_duration
            FROM execution_patterns
            WHERE task_type = ? AND success = 1
            GROUP BY tool_sequence
            HAVING COUNT(*) >= ?
            ORDER BY use_count DESC
        """, (task_type, min_examples))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "tool_sequence": json.loads(row[0]),
                "use_count": row[1],
                "avg_duration_ms": row[2]
            }
            for row in rows
        ]
    
    def get_error_recovery_strategies(
        self,
        error_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get error recovery strategies.
        
        Args:
            error_type: Optional filter by error type
            
        Returns:
            List of recovery strategies
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if error_type:
            cursor.execute("""
                SELECT * FROM error_recovery_strategies
                WHERE error_type = ?
                ORDER BY success_rate DESC, times_used DESC
            """, (error_type,))
        else:
            cursor.execute("""
                SELECT * FROM error_recovery_strategies
                ORDER BY success_rate DESC, times_used DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_task_metrics(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get task execution metrics.
        
        Args:
            task_type: Optional filter by task type
            
        Returns:
            List of task metrics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if task_type:
            cursor.execute("""
                SELECT * FROM task_metrics
                WHERE task_type = ?
                ORDER BY sample_size DESC
            """, (task_type,))
        else:
            cursor.execute("""
                SELECT * FROM task_metrics
                ORDER BY sample_size DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_learned_recommendations(
        self,
        task_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get learned recommendations for a task.
        
        Args:
            task_type: Type of task
            context: Current context
            
        Returns:
            Recommendations dictionary
        """
        recommendations = {
            "effective_tools": self.get_effective_tools(task_type),
            "successful_patterns": self.get_successful_patterns(task_type),
            "recovery_strategies": self.get_error_recovery_strategies(),
            "metrics": self.get_task_metrics(task_type)
        }
        
        return recommendations
    
    def suggest_tool_sequence(
        self,
        task_type: str,
        available_tools: List[str]
    ) -> List[str]:
        """
        Suggest a tool sequence based on learned patterns.
        
        Args:
            task_type: Type of task
            available_tools: Tools that can be used
            
        Returns:
            Suggested tool sequence
        """
        patterns = self.get_successful_patterns(task_type, min_examples=1)
        
        if not patterns:
            return available_tools[:3] if available_tools else []
        
        # Find pattern that uses available tools
        for pattern in patterns:
            tool_seq = pattern["tool_sequence"]
            if all(tool in available_tools for tool in tool_seq):
                return tool_seq
        
        # Return first pattern's tools if available
        return patterns[0]["tool_sequence"][:3]
    
    def get_error_patterns(self) -> Dict[str, Any]:
        """
        Get common error patterns.
        
        Returns:
            Error pattern statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get most common errors
        cursor.execute("""
            SELECT error_type, recovery_strategy, success_rate, times_used
            FROM error_recovery_strategies
            ORDER BY times_used DESC
            LIMIT 20
        """)
        
        errors = [dict(row) for row in cursor.fetchall()]
        
        # Get failure patterns
        cursor.execute("""
            SELECT task_type, tool_sequence, COUNT(*) as failures
            FROM execution_patterns
            WHERE success = 0
            GROUP BY task_type, tool_sequence
            ORDER BY failures DESC
            LIMIT 10
        """)
        
        failures = [
            {
                "task_type": row[0],
                "tool_sequence": json.loads(row[1]),
                "failures": row[2]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "error_recovery": errors,
            "failure_patterns": failures
        }
    
    def get_autonomy_recommendations(self) -> Dict[str, Any]:
        """
        Get recommendations for autonomy level adjustments.
        
        Returns:
            Autonomy recommendations
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        recommendations = []
        
        # Check for tools with high success rates
        cursor.execute("""
            SELECT tool_name, context_type,
                   CAST(success_count AS REAL) / (success_count + failure_count) as rate
            FROM tool_effectiveness
            WHERE success_count + failure_count >= 10
            AND rate > 0.9
        """)
        
        reliable_tools = [dict(row) for row in cursor.fetchall()]
        
        if reliable_tools:
            recommendations.append({
                "type": "increase_autonomy",
                "reason": "Tools with >90% success rate can be trusted for autonomous execution",
                "tools": reliable_tools
            })
        
        # Check for unreliable patterns
        cursor.execute("""
            SELECT task_type, success_rate
            FROM task_metrics
            WHERE sample_size >= 5
            AND success_rate < 0.5
        """)
        
        struggling = [dict(row) for row in cursor.fetchall()]
        
        if struggling:
            recommendations.append({
                "type": "decrease_autonomy",
                "reason": "Tasks with <50% success rate need more supervision",
                "tasks": struggling
            })
        
        conn.close()
        
        return {
            "recommendations": recommendations,
            "reliable_tools": reliable_tools,
            "struggling_tasks": struggling
        }


# Global instance
_execution_memory = None


def get_execution_memory(db_path: str = "memory/biznode.db") -> ExecutionMemoryStore:
    """Get the global execution memory store instance."""
    global _execution_memory
    
    if _execution_memory is None:
        _execution_memory = ExecutionMemoryStore(db_path)
    
    return _execution_memory


if __name__ == "__main__":
    # Test execution memory
    store = get_execution_memory()
    
    # Record some test data
    store.record_tool_execution("query_db", "information_retrieval", True, 150)
    store.record_tool_execution("send_email", "notification", True, 500)
    store.record_tool_execution("query_db", "information_retrieval", True, 120)
    
    store.record_task_execution(
        "information_retrieval",
        ["query_db", "search_memory", "recall"],
        True,
        800
    )
    
    store.record_error_recovery(
        "connection_timeout",
        "query_db",
        "retry_with_backoff",
        True
    )
    
    # Get recommendations
    print(json.dumps(store.get_learned_recommendations("information_retrieval", {}), indent=2))
