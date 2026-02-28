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

Automation Executor
==================
Executes tool-based plans with audit logging, permissions, and learning.
"""

import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from automation.registry import TOOL_REGISTRY
from automation.schemas import TaskStatus, StepStatus

# Import governance services
try:
    from services.audit_logger import get_audit_logger
    from services.tool_permissions import get_permission_matrix
    AUDIT_LOGGING_ENABLED = True
except ImportError:
    AUDIT_LOGGING_ENABLED = False

# Import execution memory for learning
try:
    from memory.execution_memory import get_execution_memory
    EXECUTION_MEMORY_ENABLED = True
except ImportError:
    EXECUTION_MEMORY_ENABLED = False


class ExecutionResult:
    """Result of a tool execution."""
    
    def __init__(
        self,
        success: bool,
        output: Any = None,
        error: Optional[str] = None,
        execution_time_ms: int = 0
    ):
        self.success = success
        self.output = output
        self.error = error
        self.execution_time_ms = execution_time_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms
        }


class Executor:
    """
    Executes tool-based plans with proper logging, permissions, and learning.
    
    Integrates:
    - Audit logging for enterprise compliance
    - Tool permission matrix for risk-based access control
    - Execution memory for learning from task outcomes
    """
    
    def __init__(
        self,
        db_connection=None,
        tool_registry: Optional[Dict[str, Callable]] = None,
        on_step_complete: Optional[Callable] = None,
        autonomy_level: int = 1,
        user_id: Optional[str] = None
    ):
        """
        Initialize the executor.
        
        Args:
            db_connection: SQLite database connection (optional)
            tool_registry: Dictionary of tool name -> tool instance
            on_step_complete: Callback function for step completion
            autonomy_level: Autonomy level (1-3) for permission checks
            user_id: User ID for audit logging
        """
        self.db = db_connection
        self.tool_registry = tool_registry or TOOL_REGISTRY
        self.on_step_complete = on_step_complete
        self.autonomy_level = autonomy_level
        self.user_id = user_id
        
        # Initialize governance services
        self.audit_logger = None
        self.permission_matrix = None
        self.execution_memory = None
        
        if AUDIT_LOGGING_ENABLED:
            try:
                self.audit_logger = get_audit_logger()
            except Exception as e:
                print(f"Warning: Failed to initialize audit logger: {e}")
        
        if AUDIT_LOGGING_ENABLED:
            try:
                self.permission_matrix = get_permission_matrix()
            except Exception as e:
                print(f"Warning: Failed to initialize permission matrix: {e}")
        
        if EXECUTION_MEMORY_ENABLED:
            try:
                self.execution_memory = get_execution_memory()
            except Exception as e:
                print(f"Warning: Failed to initialize execution memory: {e}")
    
    def _get_tool(self, tool_name: str):
        """Get a tool from the registry."""
        tool = self.tool_registry.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        return tool
    
    def _log_step(
        self,
        task_id: str,
        step: Dict[str, Any],
        step_id: str,
        status: str,
        output: Any = None,
        error: Optional[str] = None
    ):
        """Log step execution to database."""
        if not self.db:
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO task_steps 
                (id, task_id, step_order, tool_name, input_data, output_data, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                step_id,
                task_id,
                step.get("order", 0),
                step.get("tool", ""),
                json.dumps(step.get("arguments", {})),
                json.dumps(output) if output else None,
                status,
                error
            ))
            self.db.commit()
        except Exception as e:
            print(f"Failed to log step: {e}")
    
    def _log_tool_usage(
        self,
        task_id: str,
        tool_name: str,
        request_payload: Dict[str, Any],
        response_payload: Any,
        execution_time_ms: int,
        success: bool
    ):
        """Log tool usage for analytics."""
        if not self.db:
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO tool_logs 
                (id, task_id, tool_name, request_payload, response_payload, execution_time_ms, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                task_id,
                tool_name,
                json.dumps(request_payload),
                json.dumps(response_payload) if response_payload else None,
                execution_time_ms,
                1 if success else 0
            ))
            self.db.commit()
        except Exception as e:
            print(f"Failed to log tool usage: {e}")
    
    def execute_step(
        self,
        task_id: str,
        step: Dict[str, Any],
        context_type: str = "general"
    ) -> ExecutionResult:
        """
        Execute a single step with permission checking and audit logging.
        
        Args:
            task_id: ID of the parent task
            step: Step definition with tool and arguments
            context_type: Context type for permission checking
            
        Returns:
            ExecutionResult with success/failure info
        """
        step_id = str(uuid.uuid4())
        tool_name = step.get("tool", "")
        arguments = step.get("arguments", {})
        
        # === PERMISSION CHECK ===
        if self.permission_matrix:
            validation = self.permission_matrix.validate_execution(
                tool_name, self.autonomy_level
            )
            
            if not validation["allowed"]:
                error_msg = validation["reason"] or "Tool not permitted"
                
                # Log permission denial to audit
                if self.audit_logger:
                    self.audit_logger.log_tool_denial(
                        user_id=self.user_id or "unknown",
                        tool_name=tool_name,
                        autonomy_level=self.autonomy_level,
                        reason=error_msg,
                        task_id=task_id
                    )
                
                # Log to execution memory for learning
                if self.execution_memory:
                    self.execution_memory.record_tool_execution(
                        tool_name=tool_name,
                        context_type=context_type,
                        success=False
                    )
                
                return ExecutionResult(
                    success=False,
                    error=f"Permission denied: {error_msg}",
                    execution_time_ms=0
                )
            
            # Check if approval is required
            if validation.get("requires_approval"):
                # Log approval requirement
                if self.audit_logger:
                    self.audit_logger.log_approval_required(
                        user_id=self.user_id or "unknown",
                        tool_name=tool_name,
                        task_id=task_id
                    )
        
        # Get the tool
        try:
            tool = self._get_tool(tool_name)
        except ValueError as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=0
            )
        
        # Execute the tool
        start_time = time.time()
        try:
            # Run the tool with provided arguments
            output = tool.run(**arguments)
            execution_time = int((time.time() - start_time) * 1000)
            
            # === AUDIT LOGGING ===
            if self.audit_logger:
                self.audit_logger.log_tool_execution(
                    user_id=self.user_id or "unknown",
                    tool_name=tool_name,
                    parameters=arguments,
                    result=output,
                    success=True,
                    duration_ms=execution_time,
                    task_id=task_id
                )
            
            # === EXECUTION MEMORY ===
            if self.execution_memory:
                self.execution_memory.record_tool_execution(
                    tool_name=tool_name,
                    context_type=context_type,
                    success=True,
                    duration_ms=execution_time
                )
            
            # Log successful execution
            self._log_tool_usage(
                task_id, tool_name, arguments, output,
                execution_time, True
            )
            
            # Log step completion
            self._log_step(task_id, step, step_id, "completed", output)
            
            # Callback if provided
            if self.on_step_complete:
                self.on_step_complete(task_id, step, output)
            
            return ExecutionResult(
                success=True,
                output=output,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            # === AUDIT LOGGING ===
            if self.audit_logger:
                self.audit_logger.log_tool_execution(
                    user_id=self.user_id or "unknown",
                    tool_name=tool_name,
                    parameters=arguments,
                    result={"error": error_msg},
                    success=False,
                    duration_ms=execution_time,
                    task_id=task_id
                )
            
            # === EXECUTION MEMORY ===
            if self.execution_memory:
                self.execution_memory.record_tool_execution(
                    tool_name=tool_name,
                    context_type=context_type,
                    success=False,
                    duration_ms=execution_time
                )
            
            # Log failed execution
            self._log_tool_usage(
                task_id, tool_name, arguments, {"error": error_msg},
                execution_time, False
            )
            
            # Log step failure
            self._log_step(task_id, step, step_id, "failed", error=error_msg)
            
            return ExecutionResult(
                success=False,
                error=error_msg,
                execution_time_ms=execution_time
            )
    
    def execute_plan(
        self,
        task_id: str,
        plan: Dict[str, Any],
        stop_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a full plan.
        
        Args:
            task_id: ID of the task
            plan: Plan with steps to execute
            stop_on_error: Whether to stop on first error
            
        Returns:
            Execution summary with results
        """
        steps = plan.get("steps", [])
        results = []
        
        for step in steps:
            result = self.execute_step(task_id, step)
            results.append({
                "step": step,
                "result": result.to_dict()
            })
            
            # Stop on error if configured
            if stop_on_error and not result.success:
                break
        
        # Determine overall success
        all_success = all(r["result"]["success"] for r in results)
        
        return {
            "task_id": task_id,
            "plan_id": plan.get("plan_id"),
            "success": all_success,
            "steps_completed": len(results),
            "total_steps": len(steps),
            "results": results
        }
    
    def execute_step_async(
        self,
        task_id: str,
        step: Dict[str, Any],
        callback: Optional[Callable] = None
    ):
        """
        Execute a step asynchronously.
        
        Args:
            task_id: ID of the parent task
            step: Step definition
            callback: Callback function for completion
        """
        import threading
        
        def run():
            result = self.execute_step(task_id, step)
            if callback:
                callback(result)
        
        thread = threading.Thread(target=run)
        thread.start()
        return thread


def execute_plan(task_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to execute a plan.
    
    Args:
        task_id: Task identifier
        plan: Execution plan
        
    Returns:
        Execution results
    """
    executor = Executor()
    return executor.execute_plan(task_id, plan)


if __name__ == "__main__":
    # Test the executor
    from automation.planner import Planner
    
    planner = Planner()
    plan = planner.create_plan("Check the time and send it via email")
    
    executor = Executor()
    result = executor.execute_plan("test-task-123", plan)
    
    print(json.dumps(result, indent=2))
