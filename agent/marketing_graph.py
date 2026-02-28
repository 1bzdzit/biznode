"""
BizNode Marketing Graph (Information Collection Graph)
==================================================
LangGraph workflow for collecting leads and business information.

Flow:
- User Message → Intent Classifier → Extract Structured Data → 
- Store in SQLite → Summarize + Embed → Notify Owner

This is "Marketing Mode" - collecting leads/business information from Telegram.
"""

from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from services.llm_service import (
    ask_llm,
    extract_lead_info,
    generate_embedding,
    classify_intent
)
from memory.database import (
    create_lead,
    get_lead,
    get_all_leads,
    update_lead_status,
    get_agent_identity
)
from memory.qdrant_client import store_lead_embedding
from services.telegram_service import notify_owner, format_lead_notification
from services.email_service import notify_owner_email


# === State Definition ===

class MarketingState(TypedDict):
    """State for Marketing Graph."""
    raw_input: str
    user_id: str
    intent: str
    lead_data: Dict
    lead_id: int
    status: str
    message: str
    notify_result: Dict


# === Graph Nodes ===

def intent_classifier(state: MarketingState) -> MarketingState:
    """
    Intent Classifier (Ollama)
    Determines if the message is a marketing lead.
    """
    prompt = f"""
    Classify this message:
    {state['raw_input']}
    
    Is this a:
    - marketing_lead (someone interested in services)
    - business_inquiry (question about business)
    - partnership_request (wanting to partner)
    - general_message (not business related)
    
    Return only one word.
    """
    
    intent = ask_llm(prompt).strip().lower()
    state["intent"] = intent
    return state


def is_marketing_lead(state: MarketingState) -> bool:
    """Check if intent is a marketing lead."""
    return state.get("intent") in ["marketing_lead", "partnership_request"]


def extract_lead_data(state: MarketingState) -> MarketingState:
    """
    Extract Structured Data (LLM)
    Extracts name, business, contact from message.
    """
    lead_data = extract_lead_info(state["raw_input"])
    
    # Add source
    lead_data["source"] = "telegram"
    lead_data["user_id"] = state.get("user_id", "")
    
    # Generate summary
    prompt = f"""
    Summarize this lead in one sentence:
    Name: {lead_data.get('name', 'Unknown')}
    Business: {lead_data.get('business', 'Not specified')}
    Contact: {lead_data.get('contact', 'Not provided')}
    """
    lead_data["summary"] = ask_llm(prompt)
    
    state["lead_data"] = lead_data
    return state


def store_in_sqlite(state: MarketingState) -> MarketingState:
    """
    Store in SQLite
    Persists lead to database.
    """
    lead_data = state["lead_data"]
    
    lead_id = create_lead(
        name=lead_data.get("name", ""),
        business=lead_data.get("business", ""),
        contact_info=lead_data.get("contact", ""),
        summary=lead_data.get("summary", ""),
        source=lead_data.get("source", "telegram")
    )
    
    state["lead_id"] = lead_id
    state["status"] = "stored"
    return state


def embed_and_notify(state: MarketingState) -> MarketingState:
    """
    Summarize + Embed (Qdrant)
    Stores embedding and notifies owner.
    """
    # Store in Qdrant
    if state.get("lead_id"):
        store_lead_embedding(
            lead_id=state["lead_id"],
            summary=state["lead_data"].get("summary", "")
        )
    
    # Get owner info
    identity = get_agent_identity()
    
    # Notify owner via Telegram
    notify_result = {"telegram": None, "email": None}
    
    if identity:
        owner_telegram = identity.get("owner_telegram_id")
        owner_email = identity.get("owner_email")
        
        # Prepare lead for notification
        lead = {
            "name": state["lead_data"].get("name", ""),
            "business": state["lead_data"].get("business", ""),
            "contact_info": state["lead_data"].get("contact", ""),
            "summary": state["lead_data"].get("summary", ""),
            "source": state["lead_data"].get("source", "telegram")
        }
        
        # Telegram notification
        if owner_telegram:
            message = format_lead_notification(lead)
            notify_result["telegram"] = notify_owner(owner_telegram, message)
        
        # Email notification
        if owner_email:
            notify_result["email"] = notify_owner_email(owner_email, lead)
    
    state["notify_result"] = notify_result
    state["status"] = "completed"
    return state


def handle_general_message(state: MarketingState) -> MarketingState:
    """Handle non-lead messages."""
    state["status"] = "general"
    state["message"] = "Thank you for your message. How can I help you with your business?"
    return state


def handle_business_inquiry(state: MarketingState) -> MarketingState:
    """Handle business inquiries."""
    state["status"] = "inquiry"
    
    # Could trigger RAG query here
    from memory.obsidian_layer import query_business_memory
    
    result = query_business_memory(state["raw_input"])
    state["message"] = result.get("response", "Thank you for your inquiry.")
    return state


# === Build the Graph ===

def create_marketing_graph() -> StateGraph:
    """
    Create the Marketing Information Collection Graph.
    
    START
      ↓
    Intent Classifier
      ↓
    Is Marketing Lead? ──No──→ Handle General/Business
      ↓Yes
    Extract Lead Data
      ↓
    Store in SQLite
      ↓
    Embed + Notify
      ↓
    END
    """
    graph = StateGraph(MarketingState)
    
    # Add nodes
    graph.add_node("intent_classifier", intent_classifier)
    graph.add_node("extract_lead", extract_lead_data)
    graph.add_node("store_lead", store_in_sqlite)
    graph.add_node("notify_owner", embed_and_notify)
    graph.add_node("handle_general", handle_general_message)
    graph.add_node("handle_inquiry", handle_business_inquiry)
    
    # Set entry point
    graph.set_entry_point("intent_classifier")
    
    # Add edges (no direct edge from intent_classifier — conditional routing handles it below)
    graph.add_edge("extract_lead", "store_lead")
    graph.add_edge("store_lead", "notify_owner")
    graph.add_edge("notify_owner", END)
    
    # Conditional routing from intent
    def route_intent(state: MarketingState) -> str:
        intent = state.get("intent", "")
        if intent == "marketing_lead" or intent == "partnership_request":
            return "extract_lead"
        elif intent == "business_inquiry":
            return "handle_inquiry"
        else:
            return "handle_general"
    
    graph.add_conditional_edges(
        "intent_classifier",
        route_intent
    )
    
    graph.add_edge("handle_general", END)
    graph.add_edge("handle_inquiry", END)
    
    return graph.compile()


# === Execute ===

def run_marketing_graph(
    raw_input: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Execute the marketing graph.
    
    Args:
        raw_input: User's raw message
        user_id: User's Telegram ID
    
    Returns:
        Graph execution result
    """
    graph = create_marketing_graph()
    
    initial_state = {
        "raw_input": raw_input,
        "user_id": user_id,
        "intent": "",
        "lead_data": {},
        "lead_id": 0,
        "status": "",
        "message": "",
        "notify_result": {}
    }
    
    result = graph.invoke(initial_state)
    return result


# === Quick Functions ===

def get_leads_by_status(status: str = None) -> List[Dict]:
    """Get leads filtered by status."""
    return get_all_leads(status)


def get_lead_by_id(lead_id: int) -> Dict:
    """Get a specific lead."""
    return get_lead(lead_id)


def convert_lead_to_business(lead_id: int) -> Dict:
    """Convert a lead to a registered business."""
    from memory.obsidian_layer import register_business_with_memory
    
    lead = get_lead(lead_id)
    if not lead:
        return {"error": "Lead not found"}
    
    # Register as business
    result = register_business_with_memory(
        business_name=lead.get("business", ""),
        owner_telegram_id=lead.get("contact_info", ""),
        owner_email=lead.get("contact_info", "")
    )
    
    # Update lead status
    update_lead_status(lead_id, "converted")
    
    return result


if __name__ == "__main__":
    # Test
    result = run_marketing_graph(
        "Hi, I'm interested in your textile export services. My name is John and my company is ABC Textiles. You can reach me at john@abctextiles.com",
        "123456789"
    )
    print(f"Result: {result}")
