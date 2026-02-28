"""
BizNode Agent Package
===================
LangGraph autonomous agent workflows.
"""

from agent.marketing_graph import run_marketing_graph, get_leads_by_status
from agent.decision_graph import (
    run_decision_graph,
    propose_and_execute,
    get_pending_approvals,
    approve_action,
    reject_action
)
from agent.network_graph import (
    run_network_graph,
    register_associate,
    get_associates,
    find_partners_for_lead
)

__all__ = [
    "run_marketing_graph",
    "get_leads_by_status",
    "run_decision_graph",
    "propose_and_execute",
    "get_pending_approvals",
    "approve_action",
    "reject_action",
    "run_network_graph",
    "register_associate",
    "get_associates",
    "find_partners_for_lead"
]
