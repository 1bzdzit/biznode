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

File System Tool
==============
Tool for reading and writing local files.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from tools.base import BaseTool


class FileTool(BaseTool):
    """Tool for file system operations."""
    
    name = "file_operations"
    description = "Read, write, list, and manage local files"
    category = "filesystem"
    
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "list", "delete", "exists", "info"],
                "description": "File operation to perform"
            },
            "path": {
                "type": "string",
                "description": "File or directory path"
            },
            "content": {
                "type": "string",
                "description": "Content to write (for write operation)"
            },
            "pattern": {
                "type": "string",
                "description": "Glob pattern for listing files"
            }
        },
        "required": ["operation", "path"]
    }
    
    def __init__(self, base_path: str = "."):
        """
        Initialize the file tool.
        
        Args:
            base_path: Base directory for file operations
        """
        super().__init__()
        self.base_path = Path(base_path)
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to base path."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.base_path / p
    
    def run(self, operation: str, path: str, **kwargs) -> Any:
        """
        Execute file operation.
        
        Args:
            operation: Operation to perform
            path: File/directory path
            **kwargs: Additional arguments
            
        Returns:
            Operation result
        """
        resolved_path = self._resolve_path(path)
        
        if operation == "read":
            return self._read_file(resolved_path)
        elif operation == "write":
            content = kwargs.get("content", "")
            return self._write_file(resolved_path, content)
        elif operation == "list":
            pattern = kwargs.get("pattern", "*")
            return self._list_files(resolved_path, pattern)
        elif operation == "delete":
            return self._delete_file(resolved_path)
        elif operation == "exists":
            return self._file_exists(resolved_path)
        elif operation == "info":
            return self._file_info(resolved_path)
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
    
    def _read_file(self, path: Path) -> Dict[str, Any]:
        """Read a file."""
        try:
            if not path.exists():
                return {"success": False, "error": "File not found"}
            
            if path.is_dir():
                return {"success": False, "error": "Path is a directory"}
            
            content = path.read_text(encoding='utf-8')
            return {
                "success": True,
                "content": content,
                "size": path.stat().st_size
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _write_file(self, path: Path, content: str) -> Dict[str, Any]:
        """Write to a file."""
        try:
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            path.write_text(content, encoding='utf-8')
            return {
                "success": True,
                "path": str(path),
                "size": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _list_files(self, path: Path, pattern: str) -> Dict[str, Any]:
        """List files in a directory."""
        try:
            if not path.exists():
                return {"success": False, "error": "Directory not found"}
            
            if not path.is_dir():
                return {"success": False, "error": "Path is not a directory"}
            
            files = []
            for p in path.glob(pattern):
                if p.is_file():
                    files.append({
                        "name": p.name,
                        "path": str(p),
                        "size": p.stat().st_size
                    })
            
            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _delete_file(self, path: Path) -> Dict[str, Any]:
        """Delete a file."""
        try:
            if not path.exists():
                return {"success": False, "error": "File not found"}
            
            path.unlink()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _file_exists(self, path: Path) -> Dict[str, Any]:
        """Check if file exists."""
        return {"success": True, "exists": path.exists()}
    
    def _file_info(self, path: Path) -> Dict[str, Any]:
        """Get file information."""
        try:
            if not path.exists():
                return {"success": False, "error": "File not found"}
            
            stat = path.stat()
            return {
                "success": True,
                "info": {
                    "name": path.name,
                    "path": str(path),
                    "is_file": path.is_file(),
                    "is_dir": path.is_dir(),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "created": stat.st_ctime
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class ReadFileTool(BaseTool):
    """Tool specifically for reading files."""
    
    name = "read_file"
    description = "Read content from a file"
    category = "filesystem"
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "encoding": {"type": "string", "default": "utf-8", "description": "File encoding"}
        },
        "required": ["path"]
    }
    
    def run(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file content."""
        file_tool = FileTool()
        return file_tool.run("read", path, encoding=encoding)


class WriteFileTool(BaseTool):
    """Tool specifically for writing files."""
    
    name = "write_file"
    description = "Write content to a file"
    category = "filesystem"
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "Content to write"}
        },
        "required": ["path", "content"]
    }
    
    def run(self, path: str, content: str) -> Dict[str, Any]:
        """Write file content."""
        file_tool = FileTool()
        return file_tool.run("write", path, content=content)
