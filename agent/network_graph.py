"""
BizNode Network Graph (1bz Associate Network)
=========================================
LangGraph workflow for associate network interactions.

Flow:
- AI Identifies Opportunity → Search Associates → 
- Select Relevant Partner → Send Telegram/Email → Log Interaction

This enables:
- Partner discovery
- Network communication
- Business referrals
- Collaboration logging
"""

from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from services.llm_service import ask_llm
from memory.database import (
    get_associates_by_role,
    get_all_associates,
    get_associate,
    create_associate,
    log_network_interaction,
    get_agent_identity
)
from services.telegram_service import send_to_user, format_network_intro
from services.email_service import send_agent_email, format_network_intro_email


# === State Definition ===

class NetworkState(TypedDict):
    """State for Network Graph."""
    opportunity_type: str
    lead_data: Dict
    matched_associates: List[Dict]
    selected_associate: Dict
    communication_type: str
    message_content: str
    send_result: Dict
    status: str


# === Graph Nodes ===

def identify_opportunity(state: NetworkState) -> NetworkState:
    """
    Identify Opportunity Type
    Determines what kind of partner is needed.
    """
    lead = state.get("lead_data", {})
    business = lead.get("business", "")
    
    prompt = f"""
    What type of associate partner would be relevant for this business?
    Business: {business}
    
    Roles: logistics, marketing, legal, finance, supplier, distributor, retail
    
    Return the most relevant role.
    """
    
    role = ask_llm(prompt).strip().lower()
    state["opportunity_type"] = role
    return state


def search_associates(state: NetworkState) -> NetworkState:
    """
    Search Associates Table
    Finds partners with matching role.
    """
    role = state.get("opportunity_type", "")
    
    # Try to find associates with matching role
    associates = get_associates_by_role(role)
    
    if not associates:
        # Try broader search
        associates = get_all_associates()
    
    state["matched_associates"] = associates
    return state


def select_best_associate(state: NetworkState) -> NetworkState:
    """
    Select Relevant Partner
    Uses LLM to pick the best match.
    """
    associates = state.get("matched_associates", [])
    lead = state.get("lead_data", {})
    
    if not associates:
        state["selected_associate"] = None
        state["status"] = "no_associates"
        return state
    
    if len(associates) == 1:
        state["selected_associate"] = associates[0]
    else:
        # Use LLM to select best match
        associates_str = "\n".join([
            f"- {a.get('name', 'Unknown')} ({a.get('role', '')})"
            for a in associates
        ])
        
        prompt = f"""
        Select the best matching associate for this lead:
        
        Lead: {lead.get('name', '')} - {lead.get('business', '')}
        
        Associates:
        {associates_str}
        
        Return the name of the best match.
        """
        
        selected_name = ask_llm(prompt).strip()
        
        # Find the selected associate
        for a in associates:
            if selected_name.lower() in a.get("name", "").lower():
                state["selected_associate"] = a
                break
        else:
            state["selected_associate"] = associates[0]
    
    return state


def draft_communication(state: NetworkState) -> NetworkState:
    """
    Draft Communication Content
    Creates intro message using LLM.
    """
    lead = state.get("lead_data", {})
    associate = state.get("selected_associate", {})
    
    prompt = f"""
    Draft a brief introduction message to connect:
    
    Associate: {associate.get('name', '')} (Role: {associate.get('role', '')})
    Lead: {lead.get('name', '')} - {lead.get('business', '')}
    
    Keep it professional and concise. Maximum 2 sentences.
    """
    
    message = ask_llm(prompt)
    state["message_content"] = message
    return state


def send_telegram_message(state: NetworkState) -> NetworkState:
    """
    Send Telegram Message
    Sends intro to associate via Telegram.
    """
    associate = state.get("selected_associate", {})
    message = state.get("message_content", "")
    
    if not associate.get("telegram_id"):
        state["send_result"] = {"success": False, "error": "No Telegram ID"}
        return state
    
    # Format message
    full_message = f"""
🤝 *Network Introduction*
    
{message}
    
---
*Lead Details:*
- Name: {state['lead_data'].get('name', 'Unknown')}
- Business: {state['lead_data'].get('business', '')}
- Contact: {state['lead_data'].get('contact_info', '')}
"""
    
    result = send_to_user(associate["telegram_id"], full_message)
    
    state["send_result"] = result
    state["communication_type"] = "telegram"
    
    return state


def send_email_message(state: NetworkState) -> NetworkState:
    """
    Send Email
    Sends intro to associate via email.
    """
    associate = state.get("selected_associate", {})
    message = state.get("message_content", "")
    
    if not associate.get("email"):
        state["send_result"] = {"success": False, "error": "No email"}
        return state
    
    subject = "🤝 Network Introduction from BizNode"
    body = f"""
Hello {associate.get('name', '')},

{message}

---
Lead Details:
- Name: {state['lead_data'].get('name', 'Unknown')}
- Business: {state['lead_data'].get('business', '')}
- Contact: {state['lead_data'].get('contact_info', '')}

---
This introduction is from your BizNode AI Agent.
"""
    
    result = send_agent_email(associate["email"], subject, body)
    
    state["send_result"] = result
    state["communication_type"] = "email"
    
    return state


def log_interaction(state: NetworkState) -> NetworkState:
    """
    Log Interaction
    Records the network activity in SQLite.
    """
    associate = state.get("selected_associate", {})
    
    if associate:
        log_network_interaction(
            associate_id=associate.get("id"),
            interaction_type="introduction",
            description=f"Network introduction for {state['lead_data'].get('name', 'Unknown')}",
            initiated_by="ai_agent"
        )
    
    state["status"] = "completed"
    return state


# === Build the Graph ===

def create_network_graph() -> StateGraph:
    """
    Create the 1bz Associate Network Graph.
    
    START
      ↓
    Identify Opportunity
      ↓
    Search Associates
      ↓
    Select Best Associate
      ↓
    Draft Communication
      ↓
    Send Telegram ──→ Log Interaction → END
      ↓
    Send Email ──────→ END
    """
    graph = StateGraph(NetworkState)
    
    # Add nodes
    graph.add_node("identify_opportunity", identify_opportunity)
    graph.add_node("search_associates", search_associates)
    graph.add_node("select_associate", select_best_associate)
    graph.add_node("draft_communication", draft_communication)
    graph.add_node("send_telegram", send_telegram_message)
    graph.add_node("send_email", send_email_message)
    graph.add_node("log_interaction", log_interaction)
    
    # Entry point
    graph.set_entry_point("identify_opportunity")
    graph.add_edge("identify_opportunity", "search_associates")
    graph.add_edge("search_associates", "select_associate")
    graph.add_edge("select_associate", "draft_communication")
    
    # Communication routing
    def route_communication(state: NetworkState) -> str:
        associate = state.get("selected_associate")
        
        if not associate:
            return "log_interaction"
        
        # Send via both if available
        if associate.get("telegram_id") and associate.get("email"):
            return "send_telegram"
        elif associate.get("telegram_id"):
            return "send_telegram"
        elif associate.get("email"):
            return "send_email"
        else:
            return "log_interaction"
    
    graph.add_conditional_edges(
        "draft_communication",
        route_communication
    )
    
    # Both lead to logging
    graph.add_edge("send_telegram", "log_interaction")
    graph.add_edge("send_email", "log_interaction")
    graph.add_edge("log_interaction", END)
    
    return graph.compile()


# === Execute ===

def run_network_graph(
    lead_data: Dict,
    communication_channel: str = "both"
) -> Dict[str, Any]:
    """
    Execute the network graph.
    
    Args:
        lead_data: Lead information
        communication_channel: telegram, email, or both
    
    Returns:
        Graph execution result
    """
    graph = create_network_graph()
    
    initial_state = {
        "opportunity_type": "",
        "lead_data": lead_data,
        "matched_associates": [],
        "selected_associate": None,
        "communication_type": "",
        "message_content": "",
        "send_result": {},
        "status": ""
    }
    
    result = graph.invoke(initial_state)
    return result


# === Associate Management ===

def register_associate(
    network_id: str,
    name: str,
    telegram_id: str,
    email: str,
    role: str,
    business_type: str = ""
) -> int:
    """Register a new associate in the network."""
    return create_associate(
        network_id=network_id,
        name=name,
        telegram_id=telegram_id,
        email=email,
        role=role,
        business_type=business_type
    )


def get_associates(role: str = None) -> List[Dict]:
    """Get all associates, optionally filtered by role."""
    if role:
        return get_associates_by_role(role)
    return get_all_associates()


def find_partners_for_lead(lead: Dict) -> List[Dict]:
    """Find potential partners for a lead."""
    result = run_network_graph(lead_data=lead)
    return result.get("matched_associates", [])


if __name__ == "__main__":
    # Test
    lead = {
        "name": "John Smith",
        "business": "ABC Textiles",
        "contact_info": "john@abctextiles.com"
    }
    
    result = run_network_graph(lead_data=lead)
    print(f"Result: {result}")
