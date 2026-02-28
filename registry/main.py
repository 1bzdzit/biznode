"""
BizNode Registry — FastAPI Backend
====================================
Off-chain intelligence layer for the 1bz BizNode network.

Endpoints:
  GET  /                          Health check
  GET  /node/{node_hash}          Get node metadata
  POST /node/register             Register node (off-chain metadata)
  POST /node/{node_hash}/heartbeat Update last_seen + IP
  GET  /dns/{dns_name}            Resolve 1bz DNS name
  GET  /dns/reverse/{node_hash}   Reverse DNS lookup
  GET  /verify                    Check verification status (legacy compat)
  POST /node/{node_hash}/endorse  Add peer endorsement
  POST /node/{node_hash}/complain File a complaint
  GET  /nodes                     List all active nodes (paginated)
  POST /admin/rescore/{node_hash} Force trust score recomputation

Run:
    uvicorn registry.main:app --host 0.0.0.0 --port 8000 --reload

Dependencies:
    pip install fastapi uvicorn sqlalchemy pydantic
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from registry.models import NodeRecord, init_db, get_db
from registry.trust_engine import update_node_trust
from registry.dns_resolver import BizNodeDNSResolver

logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="BizNode Registry",
    description="Off-chain intelligence layer for the 1bz BizNode network",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    logger.info("BizNode Registry started. DB initialized.")


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class NodeRegisterRequest(BaseModel):
    node_hash:  str = Field(..., description="keccak256(node_id) hex string (0x...)")
    node_id:    str = Field(..., description="SHA-256 hex of public key")
    public_key: Optional[str] = Field(None, description="PEM-encoded Ed25519 public key")
    wallet:     Optional[str] = Field(None, description="Ethereum wallet address")
    dns_name:   Optional[str] = Field(None, description="1bz alias, e.g. shashi.1bz")
    ip_address: Optional[str] = Field(None, description="Node IP address")


class HeartbeatRequest(BaseModel):
    ip_address: Optional[str] = None


class NodeResponse(BaseModel):
    node_hash:   str
    node_id:     str
    wallet:      Optional[str]
    dns_name:    Optional[str]
    verified:    bool
    trust_score: float
    trust_tier:  str
    ip_address:  Optional[str]
    last_seen:   Optional[str]
    active:      bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": "BizNode Registry", "version": "1.0.0"}


@app.get("/node/{node_hash}", response_model=NodeResponse, tags=["Nodes"])
def get_node(node_hash: str, db=Depends(get_db)):
    """Get full metadata for a node by its nodeHash."""
    node = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    d = node.to_dict()
    return NodeResponse(**{k: d.get(k) for k in NodeResponse.__fields__})


@app.post("/node/register", tags=["Nodes"])
def register_node(req: NodeRegisterRequest, db=Depends(get_db)):
    """Register or update off-chain metadata for a node.

    Called by the node itself after on-chain registration.
    """
    existing = db.query(NodeRecord).filter_by(node_hash=req.node_hash).first()

    if existing:
        # Update metadata
        if req.public_key:  existing.public_key = req.public_key
        if req.ip_address:  existing.ip_address = req.ip_address
        if req.node_id:     existing.node_id    = req.node_id
        existing.last_seen = datetime.utcnow()
        db.commit()
        return {"status": "updated", "node_hash": req.node_hash}

    node = NodeRecord(
        node_hash  = req.node_hash,
        node_id    = req.node_id,
        public_key = req.public_key,
        wallet     = req.wallet,
        dns_name   = req.dns_name,
        ip_address = req.ip_address,
        last_seen  = datetime.utcnow(),
    )
    db.add(node)
    db.commit()
    return {"status": "registered", "node_hash": req.node_hash}


@app.post("/node/{node_hash}/heartbeat", tags=["Nodes"])
def heartbeat(node_hash: str, req: HeartbeatRequest, db=Depends(get_db)):
    """Update last_seen timestamp and optionally IP address."""
    node = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.last_seen = datetime.utcnow()
    if req.ip_address:
        node.ip_address = req.ip_address

    # Update uptime score (simple: if seen recently, uptime is good)
    node.uptime_score = min(1.0, node.uptime_score + 0.01)
    db.commit()

    return {"status": "ok", "last_seen": node.last_seen.isoformat()}


@app.get("/dns/{dns_name}", tags=["DNS"])
def resolve_dns(dns_name: str, db=Depends(get_db)):
    """Resolve a 1bz DNS name to node metadata.

    Example: GET /dns/shashi.1bz
    """
    resolver = BizNodeDNSResolver(db_session=db)
    record = resolver.resolve(dns_name)

    if not record:
        raise HTTPException(status_code=404, detail=f"DNS name '{dns_name}' not found")

    return record.to_dict()


@app.get("/dns/reverse/{node_hash}", tags=["DNS"])
def reverse_dns(node_hash: str, db=Depends(get_db)):
    """Reverse DNS: nodeHash → dns_name."""
    resolver = BizNodeDNSResolver(db_session=db)
    dns_name = resolver.reverse_lookup(node_hash)

    if not dns_name:
        raise HTTPException(status_code=404, detail="No DNS name found for this node")

    return {"node_hash": node_hash, "dns_name": dns_name}


@app.get("/verify", tags=["Verification"])
def verify_entity(entity: str = Query(..., description="entity_slug or dns_name"), db=Depends(get_db)):
    """Legacy verification endpoint — returns status for a given entity slug."""
    node = db.query(NodeRecord).filter(
        (NodeRecord.dns_name == entity) | (NodeRecord.node_id == entity)
    ).first()

    if not node:
        return {"status": "UNVERIFIED"}

    return {"status": node.trust_tier, "trust_score": node.trust_score}


@app.post("/node/{node_hash}/endorse", tags=["Trust"])
def endorse_node(node_hash: str, db=Depends(get_db)):
    """Add a peer endorsement to a node and recompute trust score."""
    node = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.endorsement_count += 1
    db.commit()

    score, tier = update_node_trust(db, node_hash)
    return {"status": "endorsed", "trust_score": score, "trust_tier": tier}


@app.post("/node/{node_hash}/complain", tags=["Trust"])
def complain_node(node_hash: str, db=Depends(get_db)):
    """File a complaint against a node and recompute trust score."""
    node = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.complaint_count += 1
    db.commit()

    score, tier = update_node_trust(db, node_hash)
    return {"status": "complaint_filed", "trust_score": score, "trust_tier": tier}


@app.get("/nodes", tags=["Nodes"])
def list_nodes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    verified_only: bool = Query(False),
    db=Depends(get_db),
):
    """List all active nodes, optionally filtered to verified only."""
    query = db.query(NodeRecord).filter_by(active=True)
    if verified_only:
        query = query.filter_by(verified=True)
    nodes = query.offset(skip).limit(limit).all()
    return [n.to_dict() for n in nodes]


@app.post("/admin/rescore/{node_hash}", tags=["Admin"])
def rescore_node(node_hash: str, db=Depends(get_db)):
    """Force recomputation of trust score for a node."""
    try:
        score, tier = update_node_trust(db, node_hash)
        return {"node_hash": node_hash, "trust_score": score, "trust_tier": tier}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
