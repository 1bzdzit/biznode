"""
BizNode Router Graph (Multi-Bot Orchestration)
=========================================
LangGraph workflow for routing requests to appropriate bots.

Architecture:
- One Telegram channel controlling multiple business bots
- Each bot may have separate memory or shared memory
- LLM-based routing logic

Bots:
- Finance Bot
- Marketing Bot
- Legal Bot
- Core Bot
"""

from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from services.llm_service import classify_intent, ask_llm


# === State Definition ===

class RouterState(TypedDict):
    """State for Router Graph."""
    query: str
    user_id: str
    intent: str
    route: str
    target_graph: str
    response: str
    status: str


# === Graph Nodes ===

def classify_intent_llm(state: RouterState) -> RouterState:
    """
    Intent Classification (LLM)
    Classifies request into: finance, marketing, legal, core
    """
    prompt = f"""
    Classify this request into one of these categories:
    finance, marketing, legal, core
    
    Request:
    {state['query']}
    
    Return only the category name in lowercase.
    """
    
    intent = ask_llm(prompt).strip().lower()
    
    # Validate intent
    valid_intents = ["finance", "marketing", "legal", "core"]
    if intent not in valid_intents:
        intent = "core"
    
    state["intent"] = intent
    return state


def determine_route(state: RouterState) -> RouterState:
    """
    Which Bot?
    Maps intent to target graph.
    """
    intent = state.get("intent", "core")
    
    route_map = {
        "finance": "finance_graph",
        "marketing": "marketing_graph",
        "legal": "legal_graph",
        "core": "core_graph"
    }
    
    state["route"] = intent
    state["target_graph"] = route_map.get(intent, "core_graph")
    return state


def execute_target_graph(state: RouterState) -> RouterState:
    """
    Call Target Bot Graph
    Routes to appropriate subgraph.
    """
    target = state.get("target_graph", "core_graph")
    query = state.get("query", "")
    
    if target == "marketing_graph":
        from agent.marketing_graph import run_marketing_graph
        result = run_marketing_graph(query, state.get("user_id", ""))
        state["response"] = result.get("message", "Processed by marketing")
    
    elif target == "finance_graph":
        from graphs.rag_query_graph import run_rag_query
        result = run_rag_query(query)
        state["response"] = result.get("response", "Processed by finance")
    
    elif target == "legal_graph":
        from graphs.rag_query_graph import run_rag_query
        result = run_rag_query(query)
        state["response"] = result.get("response", "Processed by legal")
    
    else:  # core
        from graphs.rag_query_graph import run_rag_query
        result = run_rag_query(query)
        state["response"] = result.get("response", "Processed by core")
    
    state["status"] = "completed"
    return state


# === Build the Graph ===

def create_router_graph() -> StateGraph:
    """
    Create the Multi-Bot Router Graph.
    
    START
      ↓
    Intent Classifier
      ↓
    Which Bot?
      ├── Finance Bot
      ├── Marketing Bot
      ├── Legal Bot
      └── Core Bot
      ↓
    Call Target Graph
      ↓
    END
    """
    graph = StateGraph(RouterState)
    
    # Add nodes
    graph.add_node("classify_intent", classify_intent_llm)
    graph.add_node("determine_route", determine_route)
    graph.add_node("execute_graph", execute_target_graph)
    
    # Edges
    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "determine_route")
    graph.add_edge("determine_route", "execute_graph")
    graph.add_edge("execute_graph", END)
    
    return graph.compile()


# === Execute ===

def route_query(query: str, user_id: str) -> Dict[str, Any]:
    """
    Route a query to the appropriate bot.
    
    Args:
        query: User's query
        user_id: User's ID
    
    Returns:
        Routing result
    """
    graph = create_router_graph()
    
    initial_state = {
        "query": query,
        "user_id": user_id,
        "intent": "",
        "route": "",
        "target_graph": "",
        "response": "",
        "status": ""
    }
    
    result = graph.invoke(initial_state)
    return result


# === Quick Route ===

def quick_route(query: str) -> str:
    """Quick route without full state."""
    result = route_query(query, "unknown")
    return result.get("response", "Could not process request.")


if __name__ == "__main__":
    # Test
    result = route_query("I need help with marketing strategy", "123456")
    print(f"Route: {result.get('route')}")
    print(f"Response: {result.get('response')}")
