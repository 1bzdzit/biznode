"""
BizNode RAG Query Graph
====================
LangGraph workflow for RAG (Retrieval-Augmented Generation) queries.

This is the operational intelligence layer for daily operations:

User: "Show marketing strategies for textile exports"

Flow:
- Embed User Query → Search Local Qdrant → Fetch Top-K Notes →
- Fetch Structured Data → Construct Context → Ask Ollama → Return Response

This keeps Qwen2.5 central in all queries.
"""

from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from services.llm_service import (
    generate_embedding,
    generate_response,
    ask_biznode
)
from memory.database import (
    get_business,
    get_all_businesses,
    search_businesses
)
from memory.qdrant_client import QdrantMemory


# === State Definition ===

class RAGState(TypedDict):
    """State for RAG Query Graph."""
    query: str
    embedding: List[float]
    semantic_results: List[Dict]
    structured_results: List[Dict]
    context: str
    response: str
    status: str


# === Graph Nodes ===

def embed_query(state: RAGState) -> RAGState:
    """
    Embed User Query
    Converts query to vector using Ollama.
    """
    embedding = generate_embedding(state["query"])
    state["embedding"] = embedding
    return state


def search_qdrant(state: RAGState) -> RAGState:
    """
    Search Local Qdrant
    Performs semantic search.
    """
    if not state.get("embedding"):
        state["semantic_results"] = []
        return state
    
    qdrant = QdrantMemory()
    results = qdrant.search_similar(
        vector=state["embedding"],
        limit=5,
        score_threshold=0.5
    )
    
    state["semantic_results"] = results
    return state


def fetch_structured_data(state: RAGState) -> RAGState:
    """
    Fetch Structured Data (SQLite)
    Gets business metadata for context.
    """
    structured_results = []
    
    for result in state.get("semantic_results", []):
        payload = result.get("payload", {})
        node_id = payload.get("node_id")
        
        if node_id:
            business = get_business(node_id)
            if business:
                structured_results.append(business)
    
    state["structured_results"] = structured_results
    return state


def construct_context(state: RAGState) -> RAGState:
    """
    Construct Context
    Combines semantic and structured data.
    """
    context_parts = []
    
    # Add semantic results
    for result in state.get("semantic_results", []):
        payload = result.get("payload", {})
        context_parts.append(
            f"--- Note ---\n"
            f"Title: {payload.get('title', 'Untitled')}\n"
            f"Summary: {payload.get('summary', '')}\n"
            f"Tags: {payload.get('tags', '')}"
        )
    
    # Add structured results
    for business in state.get("structured_results", []):
        context_parts.append(
            f"--- Business ---\n"
            f"Name: {business.get('business_name', '')}\n"
            f"Status: {business.get('status', '')}\n"
            f"Node ID: {business.get('node_id', '')}"
        )
    
    context = "\n\n".join(context_parts)
    state["context"] = context
    return state


def generate_rag_response(state: RAGState) -> RAGState:
    """
    Ask Ollama (Qwen2.5)
    Generates response using LLM with context.
    """
    context = state.get("context", "")
    query = state.get("query", "")
    
    if not context:
        # No context - just answer directly
        response = ask_biznode(query)
    else:
        response = generate_response(context, query)
    
    state["response"] = response
    state["status"] = "completed"
    return state


# === Build the Graph ===

def create_rag_graph() -> StateGraph:
    """
    Create the RAG Query Graph.
    
    START
      ↓
    Embed Query
      ↓
    Search Qdrant
      ↓
    Fetch Structured Data
      ↓
    Construct Context
      ↓
    Generate Response
      ↓
    END
    """
    graph = StateGraph(RAGState)
    
    # Add nodes
    graph.add_node("embed_query", embed_query)
    graph.add_node("search_qdrant", search_qdrant)
    graph.add_node("fetch_structured", fetch_structured_data)
    graph.add_node("construct_context", construct_context)
    graph.add_node("generate_response", generate_rag_response)
    
    # Edges
    graph.set_entry_point("embed_query")
    graph.add_edge("embed_query", "search_qdrant")
    graph.add_edge("search_qdrant", "fetch_structured")
    graph.add_edge("fetch_structured", "construct_context")
    graph.add_edge("construct_context", "generate_response")
    graph.add_edge("generate_response", END)
    
    return graph.compile()


# === Execute ===

def run_rag_query(query: str) -> Dict[str, Any]:
    """
    Execute a RAG query.
    
    Args:
        query: User's query
    
    Returns:
        Query result with response
    """
    graph = create_rag_graph()
    
    initial_state = {
        "query": query,
        "embedding": [],
        "semantic_results": [],
        "structured_results": [],
        "context": "",
        "response": "",
        "status": ""
    }
    
    result = graph.invoke(initial_state)
    return result


# === Quick Query ===

def query_memory(query: str) -> str:
    """
    Quick function to query memory.
    Returns just the response string.
    """
    result = run_rag_query(query)
    return result.get("response", "No results found.")


def search_business_info(search_term: str) -> List[Dict]:
    """Search businesses by name."""
    return search_businesses(search_term)


if __name__ == "__main__":
    # Test
    result = run_rag_query("Show marketing strategies for textile exports")
    print(f"Response: {result.get('response')}")
