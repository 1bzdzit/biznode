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

Tool Registry
============
Central registry for all available automation tools.
"""

from typing import Dict, Callable, Any, List, Optional
from tools.base import BaseTool, ToolNotFoundError


class ToolRegistry:
    """
    Registry for managing and accessing tools.
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        
        # Add to category
        category = tool.category
        if category not in self._categories:
            self._categories[category] = []
        if tool.name not in self._categories[category]:
            self._categories[category].append(tool.name)
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of the tool to unregister
        """
        if tool_name in self._tools:
            tool = self._tools[tool_name]
            category = tool.category
            del self._tools[tool_name]
            
            # Remove from category
            if category in self._categories:
                self._categories[category].remove(tool_name)
    
    def get(self, tool_name: str) -> BaseTool:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool instance
            
        Raises:
            ToolNotFoundError: If tool not found
        """
        if tool_name not in self._tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")
        return self._tools[tool_name]
    
    def has(self, tool_name: str) -> bool:
        """
        Check if a tool exists.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if tool exists, False otherwise
        """
        return tool_name in self._tools
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """
        List all tool names.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool names
        """
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """
        List all categories.
        
        Returns:
            List of category names
        """
        return list(self._categories.keys())
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get schemas for all tools.
        
        Returns:
            List of tool schemas
        """
        return [tool.get_schema() for tool in self._tools.values()]
    
    def configure_all(self, config: Dict[str, Dict[str, Any]]) -> None:
        """
        Configure all tools with settings.
        
        Args:
            config: Dictionary of tool_name -> config
        """
        for tool_name, tool_config in config.items():
            if tool_name in self._tools:
                self._tools[tool_name].configure(tool_config)


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry


def register_tool(tool: BaseTool) -> None:
    """Register a tool in the global registry."""
    _registry.register(tool)


def get_tool(tool_name: str) -> BaseTool:
    """Get a tool from the global registry."""
    return _registry.get(tool_name)


def list_tools(category: Optional[str] = None) -> List[str]:
    """List tools from the global registry."""
    return _registry.list_tools(category)


# Default tool imports - will be populated when tools are implemented
def _populate_default_tools():
    """Populate the registry with default tools."""
    try:
        from tools.db_tool import DBTool
        from tools.file_tool import FileTool
        from tools.email_tool import EmailTool
        from tools.memory_tool import MemoryTool
        from tools.telegram_tool import TelegramTool
        from tools.reminder_tool import ReminderTool
        from tools.webhook_tool import WebhookTool
        
        _registry.register(DBTool())
        _registry.register(FileTool())
        _registry.register(EmailTool())
        _registry.register(MemoryTool())
        _registry.register(TelegramTool())
        _registry.register(ReminderTool())
        _registry.register(WebhookTool())
    except ImportError as e:
        print(f"Warning: Some tools could not be loaded: {e}")


# Populate on module import
_populate_default_tools()


# Default TOOL_REGISTRY for backward compatibility
TOOL_REGISTRY = _registry._tools
