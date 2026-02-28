"""
BizNode Decision Authority Graph
=============================
LangGraph workflow for owner approval and decision making.

This implements the Owner Authority Layer:
- Owner Telegram ID = Decision Maker
- Major actions require confirmation
- Risk-based autonomy levels

Risk Levels:
- Low: Auto-execute (sending brochure, sharing contact)
- Medium: Notify owner + execute
- High: Require approval before execution

Autonomy Levels:
- Level 1: Assistive (AI suggests, owner approves)
- Level 2: Semi-autonomous (low-risk auto-executed)
- Level 3: Fully autonomous (AI negotiates, interacts)
"""

from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from services.llm_service import (
    ask_llm,
    assess_risk
)
from memory.database import (
    create_action,
    get_pending_actions,
    resolve_action,
    get_agent_identity
)
from services.telegram_service import (
    notify_owner,
    format_approval_request,
    get_approval_keyboard
)


# === State Definition ===

class DecisionState(TypedDict):
    """State for Decision Authority Graph."""
    action_type: str
    data: Dict
    proposal: str
    risk_level: str
    autonomy_level: int
    owner_telegram_id: str
    status: str
    owner_response: str
    execution_result: Dict


# === Risk Assessment ===

def assess_action_risk(state: DecisionState) -> DecisionState:
    """
    Assess Risk Level (LLM)
    Categorizes action as low, medium, or high.
    """
    action_description = f"""
    Action Type: {state['action_type']}
    Data: {state['data']}
    """
    
    risk_level = assess_risk(action_description)
    
    # Validate risk level
    if risk_level not in ["low", "medium", "high"]:
        risk_level = "medium"  # Default to medium
    
    state["risk_level"] = risk_level
    return state


# === Decision Nodes ===

def check_autonomy_level(state: DecisionState) -> DecisionState:
    """Get autonomy level from agent identity."""
    identity = get_agent_identity()
    
    if identity:
        state["autonomy_level"] = identity.get("autonomy_level", 1)
        state["owner_telegram_id"] = identity.get("owner_telegram_id", "")
    else:
        state["autonomy_level"] = 1
        state["owner_telegram_id"] = ""
    
    return state


def auto_execute_low_risk(state: DecisionState) -> DecisionState:
    """
    Auto-execute Low Risk actions.
    Sending brochure, sharing contact, intro email.
    """
    state["status"] = "auto_executed"
    state["execution_result"] = {
        "success": True,
        "message": f"Low-risk action '{state['action_type']}' auto-executed"
    }
    return state


def medium_risk_notify_and_execute(state: DecisionState) -> DecisionState:
    """
    Medium Risk: Notify owner and execute.
    Negotiation drafts, data sharing.
    """
    state["status"] = "notified_and_executed"
    
    # Notify owner
    if state.get("owner_telegram_id"):
        message = f"""
⚠️ *Medium Risk Action Executed*

Action: {state['action_type']}
Risk: MEDIUM

Data: {state.get('data', {})}

The action has been executed. You'll be notified of outcomes.
"""
        notify_owner(state["owner_telegram_id"], message)
    
    state["execution_result"] = {
        "success": True,
        "message": f"Medium-risk action '{state['action_type']}' executed with notification"
    }
    return state


def require_approval(state: DecisionState) -> DecisionState:
    """
    High Risk: Require owner approval.
    Financial commitments, contract agreements.
    """
    # Create action record
    action_id = create_action(
        action_type=state["action_type"],
        data=state["data"],
        risk_level="high"
    )
    
    state["status"] = "awaiting_approval"
    
    # Send approval request to owner
    if state.get("owner_telegram_id"):
        action_data = {
            "action_type": state["action_type"],
            "data": state["data"],
            "risk_level": "high",
            "action_id": action_id
        }
        
        message = format_approval_request(action_data)
        keyboard = get_approval_keyboard(action_id)
        
        notify_owner(
            state["owner_telegram_id"],
            message,
            reply_markup=keyboard
        )
    
    state["execution_result"] = {
        "action_id": action_id,
        "message": "Waiting for owner approval"
    }
    return state


def execute_approved_action(state: DecisionState) -> DecisionState:
    """Execute action after owner approval."""
    state["status"] = "executed_after_approval"
    state["owner_response"] = "approved"
    
    state["execution_result"] = {
        "success": True,
        "message": f"Action '{state['action_type']}' executed after approval"
    }
    return state


def handle_rejected_action(state: DecisionState) -> DecisionState:
    """Handle rejected action."""
    state["status"] = "rejected"
    state["owner_response"] = "rejected"
    
    state["execution_result"] = {
        "success": False,
        "message": f"Action '{state['action_type']}' was rejected by owner"
    }
    return state


def log_action(state: DecisionState) -> DecisionState:
    """Log action to memory."""
    # This would integrate with AI Obsidian Memory
    from memory.obsidian_layer import AIObsidianLayer
    
    obsidian = AIObsidianLayer()
    obsidian.write_memory(
        node_id=state.get("action_type", "action"),
        title=f"Action: {state.get('action_type')}",
        content=f"Type: {state.get('action_type')}\nRisk: {state.get('risk_level')}\nStatus: {state.get('status')}\nData: {state.get('data')}",
        auto_summarize=True,
        auto_tag=True
    )
    
    return state


# === Build the Graph ===

def create_decision_graph() -> StateGraph:
    """
    Create the Decision Authority Graph.
    
    START
      ↓
    Check Autonomy Level
      ↓
    Assess Risk
      ↓
    Route by Risk:
      ├─ Low → Auto Execute
      ├─ Medium → Notify + Execute
      └─ High → Require Approval
      ↓
    Log Action
      ↓
    END
    """
    graph = StateGraph(DecisionState)
    
    # Add nodes
    graph.add_node("check_autonomy", check_autonomy_level)
    graph.add_node("assess_risk", assess_action_risk)
    graph.add_node("auto_execute", auto_execute_low_risk)
    graph.add_node("medium_execute", medium_risk_notify_and_execute)
    graph.add_node("require_approval", require_approval)
    graph.add_node("execute_approved", execute_approved_action)
    graph.add_node("handle_rejected", handle_rejected_action)
    graph.add_node("log_action", log_action)
    
    # Entry point
    graph.set_entry_point("check_autonomy")
    graph.add_edge("check_autonomy", "assess_risk")
    
    # Conditional routing based on risk
    def route_by_risk(state: DecisionState) -> str:
        risk = state.get("risk_level", "low")
        
        # Check autonomy level
        autonomy = state.get("autonomy_level", 1)
        
        if risk == "low":
            return "auto_execute"
        elif risk == "medium":
            if autonomy >= 2:
                return "medium_execute"  # Auto-execute medium
            else:
                return "require_approval"  # Owner approval
        else:  # high
            return "require_approval"
    
    graph.add_conditional_edges(
        "assess_risk",
        route_by_risk
    )
    
    # Approval handling
    graph.add_edge("require_approval", "log_action")
    graph.add_edge("auto_execute", "log_action")
    graph.add_edge("medium_execute", "log_action")
    graph.add_edge("execute_approved", "log_action")
    graph.add_edge("handle_rejected", "log_action")
    
    graph.add_edge("log_action", END)
    
    return graph.compile()


# === Execute ===

def run_decision_graph(
    action_type: str,
    data: Dict,
    action_id: int = None,
    response: str = None
) -> Dict[str, Any]:
    """
    Execute the decision graph.
    
    Args:
        action_type: Type of action
        data: Action data
        action_id: Existing action ID (for approval response)
        response: Owner's response (approve/reject)
    
    Returns:
        Graph execution result
    """
    # Handle approval response
    if action_id and response:
        # Resolve existing action
        resolve_action(action_id, response)
        
        if response.lower() == "approve":
            return execute_approved_action({
                "action_type": action_type,
                "data": data,
                "status": "",
                "owner_response": response,
                "execution_result": {}
            })
        else:
            return handle_rejected_action({
                "action_type": action_type,
                "data": data,
                "status": "",
                "owner_response": response,
                "execution_result": {}
            })
    
    # New action - run full graph
    graph = create_decision_graph()
    
    initial_state = {
        "action_type": action_type,
        "data": data,
        "proposal": "",
        "risk_level": "",
        "autonomy_level": 1,
        "owner_telegram_id": "",
        "status": "",
        "owner_response": "",
        "execution_result": {}
    }
    
    result = graph.invoke(initial_state)
    return result


def get_pending_approvals() -> List[Dict]:
    """Get all pending owner approvals."""
    return get_pending_actions()


def approve_action(action_id: int) -> bool:
    """Approve a pending action."""
    return resolve_action(action_id, "approved")


def reject_action(action_id: int) -> bool:
    """Reject a pending action."""
    return resolve_action(action_id, "rejected")


# === Quick Decision ===

def propose_and_execute(
    action_type: str,
    data: Dict
) -> Dict[str, Any]:
    """
    Quick function to propose and execute an action.
    Uses the decision graph internally.
    """
    return run_decision_graph(action_type, data)


if __name__ == "__main__":
    # Test
    result = run_decision_graph(
        action_type="send_intro_email",
        data={"to": "partner@example.com", "content": "Introduction email"}
    )
    print(f"Result: {result}")
