"""
AI Obsidian Memory Layer
=======================
Intelligent memory layer that sits between LangGraph, Qdrant, and Ollama.

This is what makes BizNode different from simple RAG:
- Auto-summarizes business profile
- Generates embeddings
- Creates semantic links
- Auto-tags business domain
- Maintains knowledge graph
- Provides RAG context to Telegram queries

Traditional Obsidian: Manual notes, manual links, static graph
AI Obsidian: Auto-summary, auto-embedding, auto-linking, auto-clustering, auto-tagging
"""

from typing import Dict, Any, List, Optional
from services.llm_service import (
    generate_embedding,
    summarize_note,
    generate_tags,
    ask_llm
)
from memory.database import (
    create_note,
    get_note,
    get_all_notes,
    update_note,
    delete_note,
    create_link,
    get_links_for_note,
    create_business,
    get_business,
    check_business_exists
)
from memory.qdrant_client import (
    store_note_embedding,
    store_lead_embedding,
    search_memory,
    find_similar_notes,
    QdrantMemory
)


class AIObsidianLayer:
    """
    AI Obsidian Memory Layer - The intelligent memory core of BizNode.
    
    Responsibilities:
    - Auto-summarize business profiles
    - Generate embeddings
    - Create semantic links (backlinks)
    - Auto-tag business domains
    - Maintain knowledge graph
    - Provide RAG context
    """
    
    def __init__(self):
        self.qdrant = QdrantMemory()
    
    def write_memory(
        self,
        node_id: str,
        title: str,
        content: str,
        auto_summarize: bool = True,
        auto_tag: bool = True,
        auto_link: bool = True
    ) -> Dict[str, Any]:
        """
        Write to AI Obsidian Memory.
        
        Pipeline:
        1. Summarize (LLM)
        2. Generate Tags (LLM)
        3. Embed Summary
        4. Store in Qdrant
        5. Find Similar Notes
        6. Create Backlinks
        7. Store Metadata (SQLite)
        
        Args:
            node_id: Unique node identifier
            title: Note title
            content: Raw content
            auto_summarize: Use LLM to summarize
            auto_tag: Use LLM to generate tags
            auto_link: Auto-link similar notes
        
        Returns:
            Result with note_id and summary
        """
        result = {
            "node_id": node_id,
            "title": title,
            "status": "success"
        }
        
        # Step 1: Summarize using LLM
        if auto_summarize:
            summary = summarize_note(content)
        else:
            summary = content[:200]
        result["summary"] = summary
        
        # Step 2: Generate tags using LLM
        if auto_tag:
            tags = generate_tags(content)
        else:
            tags = ""
        result["tags"] = tags
        
        # Step 3 & 4: Store in Qdrant (embed + store)
        vector_id = store_note_embedding(
            node_id=node_id,
            content=content,
            summary=summary,
            tags=tags
        )
        result["vector_id"] = vector_id
        
        # Step 5: Always store in SQLite first — Qdrant and SQLite must stay in sync
        note_id = create_note(
            node_id=node_id,
            title=title,
            content=content,
            summary=summary,
            tags=tags
        )
        result["note_id"] = note_id
        
        # Step 6: Find similar notes for auto-linking
        if auto_link and vector_id:
            qdrant_result = self.qdrant.get_by_id(vector_id)
            query_vector = qdrant_result.get("vector", []) if qdrant_result else []
            similar = find_similar_notes(query_vector, limit=5) if query_vector else []
            result["similar_notes"] = [
                {"id": s["id"], "score": s["score"], "payload": s["payload"]}
                for s in similar
            ]
            
            # Create backlinks for highly similar notes
            for s in similar:
                if s["score"] > 0.80:
                    target_id = int(s["id"]) if str(s["id"]).isdigit() else 0
                    if target_id and target_id != note_id:
                        create_link(
                            source_id=note_id,
                            target_id=target_id,
                            similarity=s["score"]
                        )
        
        return result
    
    def read_memory(
        self,
        query: str,
        limit: int = 5,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        Read from AI Obsidian Memory using semantic search.
        
        Pipeline:
        1. Embed User Query
        2. Search Local Qdrant
        3. Fetch Top-K Notes
        4. Fetch Structured Data (SQLite)
        5. Construct Context
        6. Return with optional LLM response
        
        Args:
            query: Search query
            limit: Number of results
            include_context: Include LLM-generated context
        
        Returns:
            Search results with context
        """
        # Step 1-3: Semantic search in Qdrant
        results = search_memory(query, limit=limit)
        
        # Step 4: Fetch structured data from SQLite
        structured_context = []
        for r in results:
            if r.get("payload", {}).get("node_id"):
                note = get_business(r["payload"]["node_id"])
                if note:
                    structured_context.append(note)
        
        # Step 5: Build context
        context_parts = []
        for r in results:
            payload = r.get("payload", {})
            context_parts.append(
                f"Note: {payload.get('title', 'Untitled')}\n"
                f"Summary: {payload.get('summary', '')}\n"
                f"Tags: {payload.get('tags', '')}"
            )
        
        full_context = "\n\n".join(context_parts)
        
        result = {
            "query": query,
            "semantic_results": results,
            "structured_context": structured_context,
            "context": full_context,
            "total_results": len(results)
        }
        
        # Step 6: Generate LLM response if requested
        if include_context and results:
            from services.llm_service import generate_response
            result["response"] = generate_response(full_context, query)
        
        return result
    
    def get_related(self, node_id: str, limit: int = 5) -> List[Dict]:
        """Get related notes for a specific node."""
        business = get_business(node_id)
        if not business:
            return []
        
        # Search for similar businesses
        results = search_memory(
            business.get("business_name", ""),
            limit=limit
        )
        
        return results
    
    def get_backlinks(self, note_id: int) -> List[Dict]:
        """Get all notes that link to this note."""
        return get_links_for_note(note_id)
    
    def get_knowledge_graph(self) -> Dict[str, Any]:
        """Get the full knowledge graph structure."""
        all_notes = get_all_notes()
        
        # Build graph
        nodes = []
        links = []
        
        for note in all_notes:
            nodes.append({
                "id": str(note["id"]),
                "title": note["title"],
                "tags": note["tags"],
                "summary": note["summary"]
            })
            
            # Get links for this note
            note_links = get_links_for_note(note["id"])
            for link in note_links:
                links.append({
                    "source": str(note["id"]),
                    "target": str(link.get("source_id") or link.get("target_id")),
                    "similarity": link.get("similarity", 0)
                })
        
        return {
            "nodes": nodes,
            "links": links,
            "total_notes": len(nodes)
        }
    
    def cluster_by_tag(self, tag: str = None) -> List[Dict]:
        """Cluster notes by tag."""
        all_notes = get_all_notes()
        
        if tag:
            return [n for n in all_notes if tag in (n.get("tags") or "")]
        
        # Group by tags
        clusters = {}
        for note in all_notes:
            tags = (note.get("tags") or "").split(",")
            for t in tags:
                t = t.strip()
                if t:
                    if t not in clusters:
                        clusters[t] = []
                    clusters[t].append(note)
        
        return [{"tag": k, "notes": v} for k, v in clusters.items()]


# === Business Registration with AI Obsidian ===

def register_business_with_memory(
    business_name: str,
    owner_telegram_id: str,
    owner_email: str = "",
    wallet_address: str = ""
) -> Dict[str, Any]:
    """
    Register a business with AI Obsidian Memory.
    
    Flow:
    1. Check if business exists
    2. Check semantic similarity (Qdrant)
    3. Create wallet (if needed)
    4. Store business in SQLite
    5. Embed + Store in Qdrant
    6. Activate node
    
    Args:
        business_name: Name of the business
        owner_telegram_id: Owner's Telegram ID
        owner_email: Owner's email
        wallet_address: Optional wallet address
    
    Returns:
        Registration result
    """
    obsidian = AIObsidianLayer()
    
    # Step 1: Check if business exists in SQLite
    existing = check_business_exists(business_name)
    if existing:
        return {
            "status": "exists",
            "message": f"Business '{business_name}' already registered",
            "node_id": existing["node_id"]
        }
    
    # Step 2: Check semantic similarity
    similar = search_memory(business_name, limit=3)
    if similar and similar[0].get("score", 0) > 0.85:
        return {
            "status": "possible_duplicate",
            "message": "Similar business already exists",
            "similar": similar
        }
    
    # Step 3: Generate node_id
    import uuid
    node_id = str(uuid.uuid4())[:8]
    
    # Step 4: Store in SQLite
    business_id = create_business(
        node_id=node_id,
        business_name=business_name,
        owner_telegram_id=owner_telegram_id,
        owner_email=owner_email,
        wallet_address=wallet_address
    )
    
    # Step 5: Store in AI Obsidian Memory
    memory_result = obsidian.write_memory(
        node_id=node_id,
        title=business_name,
        content=f"Business: {business_name}\nOwner: {owner_telegram_id}\nEmail: {owner_email}",
        auto_summarize=True,
        auto_tag=True,
        auto_link=True
    )
    
    return {
        "status": "registered",
        "node_id": node_id,
        "business_id": business_id,
        "memory": memory_result,
        "message": f"Business '{business_name}' registered successfully"
    }


# === Query Interface ===

def query_business_memory(query: str) -> Dict[str, Any]:
    """
    Query the business memory using RAG.
    
    This is the main interface for Telegram queries.
    """
    obsidian = AIObsidianLayer()
    return obsidian.read_memory(query, include_context=True)


# === Initialize ===

def init_memory_layer() -> AIObsidianLayer:
    """Initialize the AI Obsidian Memory Layer."""
    return AIObsidianLayer()


if __name__ == "__main__":
    obsidian = init_memory_layer()
    
    # Test write
    result = obsidian.write_memory(
        node_id="test_001",
        title="Test Business",
        content="A textile export business based in Mumbai, India."
    )
    print(f"Write result: {result}")
    
    # Test read
    read_result = obsidian.read_memory("textile business")
    print(f"Read result: {read_result}")
