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

Automation Database Schema
=========================
SQLite schema for automation tasks, steps, and logging.
"""

from enum import Enum


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(str, Enum):
    """Step status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# SQL Schema for Automation Tables
AUTOMATION_SCHEMA_SQL = """
-- TASKS TABLE
-- Main task/goal table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    goal TEXT NOT NULL,
    plan_json TEXT,
    status TEXT DEFAULT 'pending',
    result_json TEXT,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster status queries
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

-- TASK STEPS TABLE
-- Individual steps within a task
CREATE TABLE IF NOT EXISTS task_steps (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    input_data TEXT,
    output_data TEXT,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Index for task step queries
CREATE INDEX IF NOT EXISTS idx_task_steps_task_id ON task_steps(task_id);
CREATE INDEX IF NOT EXISTS idx_task_steps_status ON task_steps(status);

-- TOOL LOGS TABLE
-- Detailed logging of tool executions
CREATE TABLE IF NOT EXISTS tool_logs (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    step_id TEXT,
    tool_name TEXT NOT NULL,
    tool_input TEXT,
    tool_output TEXT,
    execution_time_ms INTEGER,
    success INTEGER DEFAULT 1,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for tool log queries
CREATE INDEX IF NOT EXISTS idx_tool_logs_task_id ON tool_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_tool_logs_tool_name ON tool_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_logs_created_at ON tool_logs(created_at);

-- AGENT MEMORY INDEX TABLE
-- Stores embeddings of task outcomes for memory recall
CREATE TABLE IF NOT EXISTS agent_memory_index (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    step_id TEXT,
    content TEXT NOT NULL,
    embedding_id TEXT,
    memory_type TEXT DEFAULT 'task_outcome',
    importance_score REAL DEFAULT 0.5,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for memory queries
CREATE INDEX IF NOT EXISTS idx_agent_memory_task_id ON agent_memory_index(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory_index(memory_type);

-- SCHEDULED TASKS TABLE
-- For recurring/scheduled tasks
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    task_type TEXT,
    cron_expression TEXT,
    interval_seconds INTEGER,
    action_json TEXT,
    enabled INTEGER DEFAULT 1,
    last_run TEXT,
    next_run TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- SCHEDULED TASK RUNS TABLE
-- History of scheduled task executions
CREATE TABLE IF NOT EXISTS scheduled_task_runs (
    id TEXT PRIMARY KEY,
    scheduled_task_id TEXT NOT NULL,
    task_id TEXT,
    status TEXT DEFAULT 'running',
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    result_json TEXT,
    error_message TEXT,
    FOREIGN KEY (scheduled_task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
);

-- WORKFLOWS TABLE
-- Stored workflow definitions
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    workflow_json TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'draft',
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- WORKFLOW EXECUTIONS TABLE
-- History of workflow runs
CREATE TABLE IF NOT EXISTS workflow_executions (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    workflow_name TEXT,
    status TEXT DEFAULT 'pending',
    input_json TEXT,
    output_json TEXT,
    error_message TEXT,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);
"""


def get_schema_sql():
    """Get the automation schema SQL."""
    return AUTOMATION_SCHEMA_SQL


def create_automation_tables(db_path: str = "memory/biznode.db"):
    """
    Create automation tables in the database.
    
    Args:
        db_path: Path to SQLite database
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript(AUTOMATION_SCHEMA_SQL)
    
    conn.commit()
    conn.close()
    
    print("Automation tables created successfully.")


if __name__ == "__main__":
    # Create tables in default location
    create_automation_tables()
