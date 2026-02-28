"""
BizNode Sync Graph (1bz Network Sync)
=================================
LangGraph workflow for decentralized network synchronization.

Flow:
- Prepare Metadata → Hash Data → Sign with Wallet →
- Broadcast to 1bz Network → Store Sync Status

This enables:
- Node discoverability
- Decentralized indexing
- Future blockchain registration
- Federated knowledge sharing
"""

import hashlib
import json
from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from memory.database import (
    create_sync_record,
    get_pending_syncs,
    mark_synced,
    get_agent_identity
)


# === State Definition ===

class SyncState(TypedDict):
    """State for Sync Graph."""
    node_id: str
    metadata: Dict
    hash_data: str
    signature: str
    broadcast_result: Dict
    status: str


# === Graph Nodes ===

def prepare_metadata(state: SyncState) -> SyncState:
    """
    Prepare Metadata
    Collects node data for sync.
    """
    identity = get_agent_identity()
    
    metadata = {
        "node_id": state.get("node_id", ""),
        "agent_name": identity.get("agent_name", "") if identity else "",
        "agent_email": identity.get("agent_email", "") if identity else "",
        "autonomy_level": identity.get("autonomy_level", 1) if identity else 1,
        "timestamp": str(__import__("datetime").datetime.now())
    }
    
    state["metadata"] = metadata
    return state


def hash_metadata(state: SyncState) -> SyncState:
    """
    Hash Data
    Creates SHA-256 hash of metadata.
    """
    metadata_str = json.dumps(state["metadata"], sort_keys=True)
    hash_data = hashlib.sha256(metadata_str.encode()).hexdigest()
    
    state["hash_data"] = hash_data
    return state


def sign_with_wallet(state: SyncState) -> SyncState:
    """
    Sign with Wallet
    Signs the hash with wallet (placeholder for future).
    """
    # For now, this is a placeholder
    # In premium version, this will use actual wallet signing
    
    hash_data = state.get("hash_data", "")
    
    # Placeholder signature
    signature = f"sig_{hash_data[:16]}"
    
    state["signature"] = signature
    return state


def broadcast_to_network(state: SyncState) -> SyncState:
    """
    Broadcast to 1bz Network
    Sends data to the decentralized network.
    """
    # Placeholder for actual network broadcast
    # In production, this would call the 1bz network API
    
    broadcast_result = {
        "success": True,
        "message": "Metadata prepared for broadcast",
        "network": "1bz",
        "hash": state.get("hash_data", "")
    }
    
    # Store in sync registry
    sync_id = create_sync_record(
        node_id=state.get("node_id", ""),
        hash_data=state.get("hash_data", ""),
        signature=state.get("signature", "")
    )
    
    broadcast_result["sync_id"] = sync_id
    
    state["broadcast_result"] = broadcast_result
    state["status"] = "broadcasted"
    return state


def store_sync_status(state: SyncState) -> SyncState:
    """
    Store Sync Status
    Updates local registry.
    """
    sync_id = state.get("broadcast_result", {}).get("sync_id")
    
    if sync_id:
        mark_synced(sync_id)
    
    state["status"] = "completed"
    return state


# === Build the Graph ===

def create_sync_graph() -> StateGraph:
    """
    Create the 1bz Network Sync Graph.
    
    START
      ↓
    Prepare Metadata
      ↓
    Hash Data
      ↓
    Sign with Wallet
      ↓
    Broadcast to Network
      ↓
    Store Sync Status
      ↓
    END
    """
    graph = StateGraph(SyncState)
    
    # Add nodes
    graph.add_node("prepare_metadata", prepare_metadata)
    graph.add_node("hash_metadata", hash_metadata)
    graph.add_node("sign_wallet", sign_with_wallet)
    graph.add_node("broadcast", broadcast_to_network)
    graph.add_node("store_status", store_sync_status)
    
    # Edges
    graph.set_entry_point("prepare_metadata")
    graph.add_edge("prepare_metadata", "hash_metadata")
    graph.add_edge("hash_metadata", "sign_wallet")
    graph.add_edge("sign_wallet", "broadcast")
    graph.add_edge("broadcast", "store_status")
    graph.add_edge("store_status", END)
    
    return graph.compile()


# === Execute ===

def run_sync(node_id: str) -> Dict[str, Any]:
    """
    Execute the sync graph.
    
    Args:
        node_id: Node to sync
    
    Returns:
        Sync result
    """
    graph = create_sync_graph()
    
    initial_state = {
        "node_id": node_id,
        "metadata": {},
        "hash_data": "",
        "signature": "",
        "broadcast_result": {},
        "status": ""
    }
    
    result = graph.invoke(initial_state)
    return result


def sync_pending() -> List[Dict]:
    """Sync all pending records."""
    pending = get_pending_syncs()
    results = []
    
    for record in pending:
        result = run_sync(record.get("node_id", ""))
        results.append(result)
    
    return results


# === Quick Functions ===

def get_sync_status() -> List[Dict]:
    """Get all sync records."""
    return get_pending_syncs()


def manual_sync(node_id: str) -> Dict:
    """Manually trigger a sync."""
    return run_sync(node_id)


if __name__ == "__main__":
    # Test
    result = run_sync("test_node_001")
    print(f"Sync result: {result}")
