"""
BizNode Qdrant Client
====================
Semantic memory storage using Qdrant vector database.
Handles embeddings storage and similarity search for AI Obsidian Memory Layer.

Qdrant = Semantic memory in the BizNode architecture.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
from typing import List, Dict, Any, Optional
import os
import uuid

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "biznode_memory"
EMBEDDING_SIZE = 768  # Default for nomic-embed-text


class QdrantMemory:
    """Qdrant client for semantic memory operations."""
    
    def __init__(self, host: str = None, port: int = None):
        """Initialize Qdrant client."""
        self.host = host or QDRANT_HOST
        self.port = port or QDRANT_PORT
        self.collection_name = COLLECTION_NAME
        
        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            self._ensure_collection()
        except Exception as e:
            print(f"Warning: Could not connect to Qdrant: {e}")
            self.client = None
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        if not self.client:
            return
            
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_SIZE,
                    distance=Distance.COSINE
                )
            )
    
    def _get_embedding_size(self) -> int:
        """Get embedding size from Ollama config if available."""
        # Try to get from environment or use default
        size = os.getenv("EMBEDDING_SIZE")
        if size:
            return int(size)
        return EMBEDDING_SIZE
    
    def store_embedding(
        self, 
        vector: List[float], 
        payload: Dict[str, Any],
        vector_id: str = None
    ) -> str:
        """
        Store an embedding with payload.
        
        Args:
            vector: Embedding vector
            payload: Metadata to store
            vector_id: Optional custom ID
        
        Returns:
            The ID of the stored vector
        """
        if not self.client:
            return None
            
        vector_id = vector_id or str(uuid.uuid4())
        
        point = PointStruct(
            id=vector_id,
            vector=vector,
            payload=payload
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        return vector_id
    
    def search_similar(
        self, 
        vector: List[float], 
        limit: int = 5,
        score_threshold: float = 0.0,
        filter_conditions: Dict = None
    ) -> List[Dict]:
        """
        Search for similar vectors.
        
        Args:
            vector: Query vector
            limit: Maximum results
            score_threshold: Minimum similarity score
            filter_conditions: Optional filter
        
        Returns:
            List of similar results with scores
        """
        if not self.client:
            return []
        
        search_params = Filter(**filter_conditions) if filter_conditions else None
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=search_params
        )
        
        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload
            }
            for r in results
        ]
    
    def get_by_id(self, vector_id: str) -> Optional[Dict]:
        """Get a vector by ID."""
        if not self.client:
            return None
            
        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[vector_id],
            with_vectors=True
        )
        
        if results:
            r = results[0]
            return {
                "id": r.id,
                "vector": r.vector,
                "payload": r.payload
            }
        return None
    
    def delete_vector(self, vector_id: str) -> bool:
        """Delete a vector by ID."""
        if not self.client:
            return False
            
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[vector_id]
        )
        return True
    
    def count_vectors(self) -> int:
        """Count total vectors in collection."""
        if not self.client:
            return 0
            
        info = self.client.get_collection(self.collection_name)
        return info.vectors_count
    
    def delete_collection(self):
        """Delete the entire collection."""
        if self.client:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()


# === Semantic Memory Functions ===

def store_note_embedding(node_id: str, content: str, summary: str, tags: str) -> str:
    """
    Store a note with its embedding in Qdrant.
    Used in Memory Write Pipeline.
    """
    from services.llm_service import generate_embedding
    
    # Generate embedding from summary
    embedding = generate_embedding(summary)
    
    if not embedding:
        return None
    
    qdrant = QdrantMemory()
    vector_id = qdrant.store_embedding(
        vector=embedding,
        payload={
            "node_id": node_id,
            "content": content,
            "summary": summary,
            "tags": tags,
            "type": "note"
        }
    )
    
    return vector_id


def store_lead_embedding(lead_id: int, summary: str) -> str:
    """
    Store a lead with its embedding in Qdrant.
    Used in Marketing Graph.
    """
    from services.llm_service import generate_embedding
    
    embedding = generate_embedding(summary)
    
    if not embedding:
        return None
    
    qdrant = QdrantMemory()
    vector_id = qdrant.store_embedding(
        vector=embedding,
        payload={
            "lead_id": lead_id,
            "summary": summary,
            "type": "lead"
        }
    )
    
    return vector_id


def search_memory(query: str, limit: int = 5) -> List[Dict]:
    """
    Search semantic memory for relevant notes.
    Used in RAG Query Graph.
    """
    from services.llm_service import generate_embedding
    
    embedding = generate_embedding(query)
    
    if not embedding:
        return []
    
    qdrant = QdrantMemory()
    results = qdrant.search_similar(
        vector=embedding,
        limit=limit,
        score_threshold=0.5
    )
    
    return results


def find_similar_notes(embedding: List[float], limit: int = 5) -> List[Dict]:
    """
    Find similar notes for auto-linking.
    Used in Memory Write Pipeline.
    """
    qdrant = QdrantMemory()
    results = qdrant.search_similar(
        vector=embedding,
        limit=limit,
        score_threshold=0.80
    )
    
    return results


def get_related_notes(note_id: str, limit: int = 5) -> List[Dict]:
    """
    Get related notes for a specific note.
    Used for backlink discovery.
    """
    qdrant = QdrantMemory()
    note = qdrant.get_by_id(note_id)
    
    if not note or "vector" not in note:
        return []
    
    results = qdrant.search_similar(
        vector=note["vector"],
        limit=limit,
        score_threshold=0.70
    )
    
    # Filter out the original note
    return [r for r in results if r["id"] != note_id]


# === Initialize Qdrant Connection ===

def init_qdrant() -> QdrantMemory:
    """Initialize and return Qdrant client."""
    return QdrantMemory()


if __name__ == "__main__":
    qdrant = init_qdrant()
    print(f"Qdrant connected. Vectors: {qdrant.count_vectors()}")
