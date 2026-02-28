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

Database Tool
============
Tool for executing SQLite database queries.
"""

import sqlite3
import json
from typing import Any, Dict, List, Optional
from tools.base import BaseTool


class DBTool(BaseTool):
    """Tool for querying the SQLite database."""
    
    name = "query_db"
    description = "Execute SQL queries on the SQLite database"
    category = "database"
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL query to execute"
            },
            "params": {
                "type": "array",
                "description": "Query parameters",
                "items": {"type": "string"}
            },
            "fetch": {
                "type": "boolean",
                "description": "Whether to fetch results (for SELECT)",
                "default": True
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        """
        Initialize the database tool.
        
        Args:
            db_path: Path to SQLite database file
        """
        super().__init__()
        self.db_path = db_path
    
    def run(self, query: str, params: Optional[List] = None, fetch: bool = True) -> Any:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results or affected row count
        """
        params = params or []
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            
            if fetch:
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                return {
                    "success": True,
                    "rows": results,
                    "count": len(results)
                }
            else:
                conn.commit()
                return {
                    "success": True,
                    "rows_affected": cursor.rowcount
                }
                
        except sqlite3.Error as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
    
    def query_businesses(self, status: Optional[str] = None) -> List[Dict]:
        """
        Query businesses with optional status filter.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of business records
        """
        if status:
            query = "SELECT * FROM businesses WHERE status = ?"
            params = [status]
        else:
            query = "SELECT * FROM businesses"
            params = []
        
        result = self.run(query, params)
        return result.get("rows", []) if result.get("success") else []
    
    def query_leads(self, status: Optional[str] = None) -> List[Dict]:
        """
        Query leads with optional status filter.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of lead records
        """
        if status:
            query = "SELECT * FROM leads WHERE status = ?"
            params = [status]
        else:
            query = "SELECT * FROM leads"
            params = []
        
        result = self.run(query, params)
        return result.get("rows", []) if result.get("success") else []


class InsertTool(BaseTool):
    """Tool for inserting records into the database."""
    
    name = "insert_db"
    description = "Insert a record into the database"
    category = "database"
    
    parameters = {
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Table name"
            },
            "data": {
                "type": "object",
                "description": "Data to insert"
            }
        },
        "required": ["table", "data"]
    }
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        super().__init__()
        self.db_path = db_path
    
    def run(self, table: str, data: Dict) -> Any:
        """Insert a record into the database."""
        if not data:
            return {"success": False, "error": "No data provided"}
        
        columns = list(data.keys())
        placeholders = ["?"] * len(columns)
        values = list(data.values())
        
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, values)
            conn.commit()
            return {
                "success": True,
                "last_row_id": cursor.lastrowid
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()


class UpdateTool(BaseTool):
    """Tool for updating database records."""
    
    name = "update_db"
    description = "Update records in the database"
    category = "database"
    
    parameters = {
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Table name"
            },
            "data": {
                "type": "object",
                "description": "Data to update"
            },
            "where": {
                "type": "string",
                "description": "WHERE clause"
            },
            "params": {
                "type": "array",
                "description": "Query parameters"
            }
        },
        "required": ["table", "data", "where"]
    }
    
    def __init__(self, db_path: str = "memory/biznode.db"):
        super().__init__()
        self.db_path = db_path
    
    def run(self, table: str, data: Dict, where: str, params: Optional[List] = None) -> Any:
        """Update records in the database."""
        if not data:
            return {"success": False, "error": "No data provided"}
        
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values())
        
        if params:
            values.extend(params)
        
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, values)
            conn.commit()
            return {
                "success": True,
                "rows_affected": cursor.rowcount
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
