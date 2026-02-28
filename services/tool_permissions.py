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

Tool Permission Matrix
====================
Enterprise-grade tool permission system for autonomous operations.
Controls which tools can be used at each autonomy level.
"""

import os
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path


# Default permission matrix
DEFAULT_PERMISSIONS = {
    # Autonomy Level 1: Assistive - AI suggests, owner approves
    "level_1": {
        "description": "Assistive - AI suggests, owner approves",
        "tools": [
            "query_db",
            "search_memory",
            "recall",
            "read_file"
        ],
        "max_concurrent_tasks": 1,
        "requires_approval": True,
        "risk_threshold": "low"
    },
    
    # Autonomy Level 2: Semi-autonomous - Low-risk actions auto-executed
    "level_2": {
        "description": "Semi-autonomous - Low-risk actions auto-executed",
        "tools": [
            "query_db",
            "search_memory",
            "recall",
            "read_file",
            "write_file",
            "send_email",
            "send_telegram",
            "create_reminder",
            "insert_db"
        ],
        "max_concurrent_tasks": 3,
        "requires_approval": True,
        "risk_threshold": "medium"
    },
    
    # Autonomy Level 3: Fully autonomous - AI negotiates, interacts
    "level_3": {
        "description": "Fully autonomous - AI negotiates, interacts",
        "tools": [
            "query_db",
            "search_memory",
            "recall",
            "read_file",
            "write_file",
            "send_email",
            "send_telegram",
            "create_reminder",
            "insert_db",
            "update_db",
            "webhook",
            "api_call",
            "trigger_webhook",
            "schedule_task"
        ],
        "max_concurrent_tasks": 10,
        "requires_approval": False,
        "risk_threshold": "high"
    }
}

# Tool risk levels
TOOL_RISK_LEVELS = {
    # Low risk - informational only
    "low": [
        "query_db",
        "search_memory",
        "recall",
        "read_file"
    ],
    
    # Medium risk - can modify data but contained
    "medium": [
        "send_email",
        "send_telegram",
        "create_reminder",
        "insert_db",
        "write_file",
        "send_reminder"
    ],
    
    # High risk - external communications, financial
    "high": [
        "update_db",
        "delete_file",
        "webhook",
        "api_call",
        "trigger_webhook",
        "schedule_task",
        "execute_code"
    ]
}


class ToolPermissionMatrix:
    """
    Manages tool permissions based on autonomy levels.
    
    Provides:
    - Tool allowlist per autonomy level
    - Risk scoring for tools
    - Approval requirement checks
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        permissions: Optional[Dict] = None
    ):
        """
        Initialize the permission matrix.
        
        Args:
            config_path: Path to YAML config file
            permissions: Optional permission dictionary
        """
        self.config_path = config_path
        self.permissions = permissions or DEFAULT_PERMISSIONS.copy()
        
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
    
    def _load_from_file(self, config_path: str):
        """Load permissions from YAML file."""
        with open(config_path, 'r') as f:
            loaded = yaml.safe_load(f)
            if loaded:
                self.permissions = loaded
    
    def _save_to_file(self):
        """Save permissions to YAML file."""
        if self.config_path:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.permissions, f, default_flow_style=False)
    
    def is_tool_allowed(
        self,
        tool_name: str,
        autonomy_level: int
    ) -> bool:
        """
        Check if a tool is allowed for an autonomy level.
        
        Args:
            tool_name: Name of the tool
            autonomy_level: Current autonomy level (1-3)
            
        Returns:
            True if tool is allowed
        """
        level_key = f"level_{autonomy_level}"
        
        if level_key not in self.permissions:
            return False
        
        allowed_tools = self.permissions[level_key].get("tools", [])
        
        return tool_name in allowed_tools
    
    def get_tool_risk_level(self, tool_name: str) -> str:
        """
        Get the risk level of a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Risk level: "low", "medium", or "high"
        """
        for risk_level, tools in TOOL_RISK_LEVELS.items():
            if tool_name in tools:
                return risk_level
        
        # Default to high risk for unknown tools
        return "high"
    
    def requires_approval(
        self,
        tool_name: str,
        autonomy_level: int
    ) -> bool:
        """
        Check if a tool requires owner approval.
        
        Args:
            tool_name: Name of the tool
            autonomy_level: Current autonomy level
            
        Returns:
            True if approval is required
        """
        # Get the autonomy level config
        level_key = f"level_{autonomy_level}"
        
        if level_key not in self.permissions:
            return True
        
        level_config = self.permissions[level_key]
        
        # Check if level requires approval
        if level_config.get("requires_approval", True):
            return True
        
        # Check tool risk level vs threshold
        tool_risk = self.get_tool_risk_level(tool_name)
        threshold = level_config.get("risk_threshold", "low")
        
        risk_order = ["low", "medium", "high"]
        
        return risk_order.index(tool_risk) > risk_order.index(threshold)
    
    def get_allowed_tools(self, autonomy_level: int) -> List[str]:
        """
        Get list of allowed tools for an autonomy level.
        
        Args:
            autonomy_level: Autonomy level (1-3)
            
        Returns:
            List of allowed tool names
        """
        level_key = f"level_{autonomy_level}"
        
        if level_key not in self.permissions:
            return []
        
        return self.permissions[level_key].get("tools", [])
    
    def get_level_config(self, autonomy_level: int) -> Dict[str, Any]:
        """
        Get full configuration for an autonomy level.
        
        Args:
            autonomy_level: Autonomy level (1-3)
            
        Returns:
            Level configuration dictionary
        """
        level_key = f"level_{autonomy_level}"
        
        return self.permissions.get(level_key, {})
    
    def validate_execution(
        self,
        tool_name: str,
        autonomy_level: int,
        risk_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate if a tool can be executed.
        
        Args:
            tool_name: Name of the tool
            autonomy_level: Current autonomy level
            risk_level: Optional explicit risk level
            
        Returns:
            Validation result with:
            - allowed: bool
            - requires_approval: bool
            - reason: str (if not allowed)
        """
        # Check if tool is allowed at all
        if not self.is_tool_allowed(tool_name, autonomy_level):
            return {
                "allowed": False,
                "requires_approval": False,
                "reason": f"Tool '{tool_name}' not permitted at autonomy level {autonomy_level}"
            }
        
        # Get tool's risk level
        actual_risk = risk_level or self.get_tool_risk_level(tool_name)
        
        # Get level's risk threshold
        level_config = self.get_level_config(autonomy_level)
        threshold = level_config.get("risk_threshold", "low")
        
        risk_order = ["low", "medium", "high"]
        
        # Check if tool exceeds threshold
        if risk_order.index(actual_risk) > risk_order.index(threshold):
            # Check if approval is required
            approval_required = self.requires_approval(tool_name, autonomy_level)
            
            return {
                "allowed": True,
                "requires_approval": approval_required,
                "reason": "Approval required for high-risk action" if approval_required else None
            }
        
        return {
            "allowed": True,
            "requires_approval": False,
            "reason": None
        }
    
    def add_tool_permission(
        self,
        tool_name: str,
        autonomy_level: int
    ):
        """Add a tool to an autonomy level's allowed list."""
        level_key = f"level_{autonomy_level}"
        
        if level_key not in self.permissions:
            self.permissions[level_key] = {
                "description": f"Level {autonomy_level}",
                "tools": [],
                "requires_approval": True
            }
        
        if tool_name not in self.permissions[level_key]["tools"]:
            self.permissions[level_key]["tools"].append(tool_name)
            self._save_to_file()
    
    def remove_tool_permission(
        self,
        tool_name: str,
        autonomy_level: int
    ):
        """Remove a tool from an autonomy level's allowed list."""
        level_key = f"level_{autonomy_level}"
        
        if level_key in self.permissions:
            tools = self.permissions[level_key].get("tools", [])
            if tool_name in tools:
                tools.remove(tool_name)
                self._save_to_file()
    
    def set_autonomy_level(
        self,
        autonomy_level: int,
        config: Dict[str, Any]
    ):
        """Set configuration for an autonomy level."""
        level_key = f"level_{autonomy_level}"
        self.permissions[level_key] = config
        self._save_to_file()


# Global instance
_permission_matrix = None


def get_permission_matrix(
    config_path: Optional[str] = None
) -> ToolPermissionMatrix:
    """
    Get the global permission matrix instance.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        ToolPermissionMatrix instance
    """
    global _permission_matrix
    
    if _permission_matrix is None:
        _permission_matrix = ToolPermissionMatrix(config_path)
    
    return _permission_matrix


# Decorator for tool permission checking
def require_tool_permission(autonomy_level_param: str = "autonomy_level"):
    """
    Decorator to check tool permissions before execution.
    
    Usage:
        @require_tool_permission()
        def execute_tool(self, tool_name: str, autonomy_level: int, ...):
            ...
    """
    def decorator(func):
        def wrapper(self, tool_name: str, *args, **kwargs):
            # Get autonomy level from kwargs or default
            autonomy_level = kwargs.get(autonomy_level_param, 1)
            
            # Get permission matrix
            matrix = get_permission_matrix()
            
            # Validate execution
            validation = matrix.validate_execution(tool_name, autonomy_level)
            
            if not validation["allowed"]:
                raise PermissionError(validation["reason"])
            
            return func(self, tool_name, *args, **kwargs)
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the permission matrix
    matrix = get_permission_matrix()
    
    # Test tool permissions
    test_cases = [
        ("query_db", 1, True),
        ("send_email", 1, False),
        ("send_email", 2, True),
        ("webhook", 3, True),
    ]
    
    for tool, level, should_pass in test_cases:
        result = matrix.validate_execution(tool, level)
        status = "✓" if result["allowed"] == should_pass else "✗"
        print(f"{status} Tool '{tool}' at level {level}: allowed={result['allowed']}")
