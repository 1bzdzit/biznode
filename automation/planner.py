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

Automation Planner
==================
Task planning layer that breaks user goals into structured tool-based steps.
Uses Ollama for reasoning and structured JSON output.
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime


# System prompt for the planner
PLANNER_SYSTEM_PROMPT = """You are BizNode Autonomous Planner, an expert business automation system.

Your job is to break down user goals into executable tool-based steps.

Available tools:
- query_db: Query SQLite database for business data
- send_email: Send emails to contacts
- read_file: Read files from the local system
- write_file: Write content to files
- search_memory: Search the AI Obsidian memory
- send_telegram: Send Telegram messages
- create_reminder: Set up a reminder/task
- check_status: Check status of business entities
- calculate: Perform calculations

Guidelines:
1. Break complex goals into simple, sequential steps
2. Each step should use exactly one tool
3. Consider dependencies between steps
4. Output ONLY valid JSON, no explanations
5. Always include reasoning for each step

Output format:
{
  "goal": "original user goal",
  "reasoning": "why this plan will work",
  "steps": [
    {
      "order": 1,
      "tool": "tool_name",
      "arguments": {"key": "value"},
      "reasoning": "why this step"
    }
  ]
}
"""


class Planner:
    """Task planner that uses LLM to create execution plans."""
    
    def __init__(self, llm_client=None):
        """
        Initialize planner with optional LLM client.
        
        Args:
            llm_client: LLM client instance (defaults to using services.llm_service)
        """
        self.llm_client = llm_client
    
    def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM."""
        if self.llm_client:
            return self.llm_client.ask(prompt, system_prompt=PLANNER_SYSTEM_PROMPT)
        
        # Default: use the services module
        try:
            from services.llm_service import ask_llm
            return ask_llm(prompt, system_prompt=PLANNER_SYSTEM_PROMPT)
        except ImportError:
            raise RuntimeError("LLM client not available. Please configure Ollama.")
    
    def create_plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an execution plan for the given goal.
        
        Args:
            goal: The user's goal/objective
            context: Optional context information (user_id, business data, etc.)
            
        Returns:
            Dictionary containing the execution plan
            
        Raises:
            ValueError: If the LLM returns invalid JSON
        """
        # Build context prompt if provided
        context_str = ""
        if context:
            context_items = [f"{k}: {v}" for k, v in context.items()]
            context_str = f"\n\nContext:\n" + "\n".join(context_items)
        
        full_prompt = f"""Create a plan for this goal:

Goal: {goal}
{context_str}

Return ONLY JSON, no other text."""
        
        # Get plan from LLM
        response = self._get_llm_response(full_prompt)
        
        # Parse JSON from response
        try:
            # Try direct parse first
            plan = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    plan = json.loads(response[json_start:json_end])
                else:
                    raise ValueError("No JSON found in response")
            except Exception as e:
                raise ValueError(f"Failed to parse planner output: {e}")
        
        # Validate plan structure
        if "steps" not in plan:
            raise ValueError("Plan must contain 'steps' array")
        
        # Add metadata
        plan["goal"] = goal
        plan["created_at"] = datetime.utcnow().isoformat()
        plan["plan_id"] = str(uuid.uuid4())
        
        return plan
    
    def validate_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Validate that a plan is well-formed.
        
        Args:
            plan: The plan to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(plan, dict):
            return False
        
        if "steps" not in plan:
            return False
        
        if not isinstance(plan["steps"], list):
            return False
        
        # Check each step has required fields
        required_step_fields = {"order", "tool", "arguments"}
        for step in plan["steps"]:
            if not isinstance(step, dict):
                return False
            if not required_step_fields.issubset(step.keys()):
                return False
        
        return True
    
    def estimate_complexity(self, plan: Dict[str, Any]) -> str:
        """
        Estimate the complexity of a plan.
        
        Args:
            plan: The plan to evaluate
            
        Returns:
            "simple", "moderate", or "complex"
        """
        step_count = len(plan.get("steps", []))
        
        if step_count <= 2:
            return "simple"
        elif step_count <= 5:
            return "moderate"
        else:
            return "complex"


def create_plan(goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to create a plan.
    
    Args:
        goal: The user's goal
        context: Optional context
        
    Returns:
        Execution plan dictionary
    """
    planner = Planner()
    return planner.create_plan(goal, context)


if __name__ == "__main__":
    # Test the planner
    planner = Planner()
    
    test_goal = "Send a reminder to all clients with overdue invoices"
    plan = planner.create_plan(test_goal)
    
    print(json.dumps(plan, indent=2))
