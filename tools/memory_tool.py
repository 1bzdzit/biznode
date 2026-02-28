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

Memory Tool
==========
Tool for searching the AI Obsidian Memory (Qdrant + SQLite).
"""

import os
from typing import Any, Dict, List, Optional
from tools.base import BaseTool


class MemoryTool(BaseTool):
    """Tool for searching the AI Obsidian Memory."""
    
    name = "search_memory"
    description = "Search the AI Obsidian memory for relevant information"
    category = "memory"
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "limit": {
                "type": "integer",
                "default": 5,
                "description": "Maximum number of results"
            },
            "collection": {
                "type": "string",
                "default": "biznode_memory",
                "description": "Qdrant collection to search"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self):
        """Initialize the memory tool."""
        super().__init__()
        self._qdrant_client = None
    
    def _get_qdrant_client(self):
        """Get or initialize Qdrant client."""
        if self._qdrant_client is None:
            try:
                from qdrant_client import QdrantClient
                
                host = os.getenv("QDRANT_HOST", "localhost")
                port = int(os.getenv("QDRANT_PORT", "6333"))
                
                self._qdrant_client = QdrantClient(host=host, port=port)
            except ImportError:
                print("Warning: Qdrant client not available")
                return None
            except Exception as e:
                print(f"Warning: Could not connect to Qdrant: {e}")
                return None
        
        return self._qdrant_client
    
    def run(
        self,
        query: str,
        limit: int = 5,
        collection: str = "biznode_memory"
    ) -> Dict[str, Any]:
        """
        Search the memory.
        
        Args:
            query: Search query
            limit: Maximum results
            collection: Collection name
            
        Returns:
            Search results
        """
        client = self._get_qdrant_client()
        
        if not client:
            return {
                "success": False,
                "error": "Qdrant not available"
            }
        
        try:
            # Generate embedding for query
            embedding = self._generate_embedding(query)
            
            if not embedding:
                return {
                    "success": False,
                    "error": "Could not generate embedding"
                }
            
            # Search
            results = client.search(
                collection_name=collection,
                query_vector=embedding,
                limit=limit
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                    "content": result.payload.get("content", "")
                })
            
            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "count": len(formatted_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        try:
            from services.llm_service import generate_embedding
            return generate_embedding(text)
        except ImportError:
            return None
    
    def store_memory(
        self,
        content: str,
        metadata: Dict[str, Any],
        collection: str = "biznode_memory"
    ) -> Dict[str, Any]:
        """
        Store content in memory.
        
        Args:
            content: Content to store
            metadata: Metadata about the content
            collection: Collection name
            
        Returns:
            Result dictionary
        """
        client = self._get_qdrant_client()
        
        if not client:
            return {
                "success": False,
                "error": "Qdrant not available"
            }
        
        try:
            # Generate embedding
            embedding = self._generate_embedding(content)
            
            if not embedding:
                return {
                    "success": False,
                    "error": "Could not generate embedding"
                }
            
            # Store
            from qdrant_client.models import PointStruct
            
            import uuid
            point_id = str(uuid.uuid4())
            
            client.upsert(
                collection_name=collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "content": content,
                            **metadata
                        }
                    )
                ]
            )
            
            return {
                "success": True,
                "id": point_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class RecallTool(BaseTool):
    """Tool for recalling past task executions."""
    
    name = "recall"
    description = "Recall similar past executions from memory"
    category = "memory"
    
    parameters = {
        "type": "object",
        "properties": {
            "task_type": {
                "type": "string",
                "description": "Type of task to recall"
            },
            "limit": {
                "type": "integer",
                "default": 5
            }
        },
        "required": ["task_type"]
    }
    
    def run(self, task_type: str, limit: int = 5) -> Dict[str, Any]:
        """
        Recall similar past tasks.
        
        Args:
            task_type: Type of task
            limit: Maximum results
            
        Returns:
            Past task results
        """
        import sqlite3
        from datetime import datetime
        
        db_path = os.getenv("SQLITE_PATH", "memory/biznode.db")
        
        if not os.path.exists(db_path):
            return {
                "success": False,
                "error": "Database not found"
            }
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Query tasks
            cursor.execute("""
                SELECT id, goal, status, created_at
                FROM tasks
                WHERE goal LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{task_type}%", limit))
            
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "task_id": row[0],
                    "goal": row[1],
                    "status": row[2],
                    "created_at": row[3]
                })
            
            conn.close()
            
            return {
                "success": True,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
