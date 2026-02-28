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

Tool Base Class
===============
Base class for all automation tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    Each tool must implement the `run` method.
    """
    
    # Tool metadata
    name: str = "base"
    description: str = "Base tool"
    category: str = "general"
    parameters: Dict[str, Any] = {}
    
    def __init__(self):
        """Initialize the tool."""
        self._config = {}
    
    def configure(self, config: Dict[str, Any]):
        """
        Configure the tool with settings.
        
        Args:
            config: Tool-specific configuration
        """
        self._config = config
    
    @abstractmethod
    def run(self, **kwargs) -> Any:
        """
        Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Tool execution result
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Tool must implement run method")
    
    def validate_arguments(self, **kwargs) -> bool:
        """
        Validate the provided arguments.
        
        Args:
            **kwargs: Arguments to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Default implementation - always valid
        # Subclasses can override for specific validation
        return True
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for this tool.
        
        Returns:
            JSON schema dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"


class ToolError(Exception):
    """Base exception for tool errors."""
    pass


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found in the registry."""
    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""
    pass


class InvalidArgumentsError(ToolError):
    """Raised when tool arguments are invalid."""
    pass
