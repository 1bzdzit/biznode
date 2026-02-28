"""
Blockchain Event Listener
=========================
Listens to BizNodeRegistry smart contract events on Polygon and
syncs them into the off-chain registry database.

Events handled:
  - NodeRegistered  → create NodeRecord in DB
  - NodeVerified    → mark node as verified, recompute trust
  - StakeAdded      → update stake amount, recompute trust
  - StakeWithdrawn  → update stake amount, recompute trust
  - NodeDeregistered → mark node inactive

Usage:
    python -m registry.event_listener

Environment variables:
    POLYGON_RPC_URL    - Polygon RPC endpoint
    CONTRACT_ADDRESS   - Deployed BizNodeRegistry address
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Config ────────────────────────────────────────────────────────────────────
RPC_URL          = os.getenv("POLYGON_RPC_URL",  "https://polygon-rpc.com")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
ABI_PATH         = Path(__file__).parent.parent / "contracts" / "abi.json"

POLL_INTERVAL = 5   # seconds between polls
CONFIRMATIONS = 2   # blocks to wait before processing


def load_abi() -> list:
    if not ABI_PATH.exists():
        raise FileNotFoundError(f"ABI not found at {ABI_PATH}. Run deploy.py first.")
    return json.loads(ABI_PATH.read_text())


def get_contract(w3):
    if not CONTRACT_ADDRESS:
        raise ValueError("CONTRACT_ADDRESS not set. Deploy the contract first.")
    abi = load_abi()
    return w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)


# ── Event processors ──────────────────────────────────────────────────────────

def process_node_registered(event, db):
    from registry.models import NodeRecord
    from registry.trust_engine import compute_trust_score, TrustInputs

    args = event["args"]
    node_hash = "0x" + args["nodeHash"].hex()
    wallet    = args["wallet"]
    dns_name  = args["dnsName"]
    timestamp = datetime.utcfromtimestamp(args["timestamp"])

    existing = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if existing:
        logger.info("NodeRegistered: already in DB, skipping. hash=%s", node_hash)
        return

    node = NodeRecord(
        node_hash    = node_hash,
        node_id      = "",          # Will be filled when node sends public key
        wallet       = wallet,
        dns_name     = dns_name,
        verified     = False,
        stake_wei    = "0",
        registered_at = timestamp,
        trust_tier   = "UNVERIFIED",
        trust_score  = 0.0,
    )
    db.add(node)
    db.commit()
    logger.info("NodeRegistered: %s → %s (%s)", node_hash, wallet, dns_name)


def process_node_verified(event, db):
    from registry.models import NodeRecord
    from registry.trust_engine import update_node_trust

    args = event["args"]
    node_hash = "0x" + args["nodeHash"].hex()

    node = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if not node:
        logger.warning("NodeVerified: node not in DB. hash=%s", node_hash)
        return

    node.verified = True
    db.commit()

    score, tier = update_node_trust(db, node_hash)
    logger.info("NodeVerified: %s → score=%.2f tier=%s", node_hash, score, tier)


def process_stake_added(event, db):
    from registry.models import NodeRecord
    from registry.trust_engine import update_node_trust

    args = event["args"]
    node_hash = "0x" + args["nodeHash"].hex()
    new_total = str(args["newTotal"])

    node = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if not node:
        logger.warning("StakeAdded: node not in DB. hash=%s", node_hash)
        return

    node.stake_wei = new_total
    db.commit()

    score, tier = update_node_trust(db, node_hash)
    logger.info("StakeAdded: %s → stake=%s score=%.2f tier=%s", node_hash, new_total, score, tier)


def process_stake_withdrawn(event, db):
    from registry.models import NodeRecord
    from registry.trust_engine import update_node_trust

    args = event["args"]
    node_hash = "0x" + args["nodeHash"].hex()

    node = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if not node:
        return

    # Re-fetch stake from chain for accuracy
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        contract = get_contract(w3)
        on_chain = contract.functions.getNode(args["nodeHash"]).call()
        node.stake_wei = str(on_chain[3])  # stakeAmount
        db.commit()
    except Exception as e:
        logger.warning("Could not refresh stake from chain: %s", e)

    score, tier = update_node_trust(db, node_hash)
    logger.info("StakeWithdrawn: %s → score=%.2f tier=%s", node_hash, score, tier)


def process_node_deregistered(event, db):
    from registry.models import NodeRecord

    args = event["args"]
    node_hash = "0x" + args["nodeHash"].hex()

    node = db.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if node:
        node.active = False
        db.commit()
        logger.info("NodeDeregistered: %s", node_hash)


EVENT_HANDLERS = {
    "NodeRegistered":   process_node_registered,
    "NodeVerified":     process_node_verified,
    "StakeAdded":       process_stake_added,
    "StakeWithdrawn":   process_stake_withdrawn,
    "NodeDeregistered": process_node_deregistered,
}


# ── Main polling loop ─────────────────────────────────────────────────────────

def run_listener():
    """Poll for new contract events and process them."""
    try:
        from web3 import Web3
    except ImportError:
        logger.critical("web3 not installed. Run: pip install web3")
        sys.exit(1)

    from registry.models import init_db, SessionLocal

    init_db()

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        logger.critical("Cannot connect to RPC: %s", RPC_URL)
        sys.exit(1)

    contract = get_contract(w3)
    logger.info("Event listener started. Contract: %s", CONTRACT_ADDRESS)

    # Track last processed block
    last_block_file = Path("registry/.last_block")
    if last_block_file.exists():
        from_block = int(last_block_file.read_text().strip())
    else:
        from_block = w3.eth.block_number - 1000  # Start from 1000 blocks ago

    while True:
        try:
            current_block = w3.eth.block_number - CONFIRMATIONS

            if current_block <= from_block:
                time.sleep(POLL_INTERVAL)
                continue

            db = SessionLocal()
            try:
                for event_name, handler in EVENT_HANDLERS.items():
                    event_obj = getattr(contract.events, event_name, None)
                    if not event_obj:
                        continue
                    events = event_obj.get_logs(fromBlock=from_block, toBlock=current_block)
                    for event in events:
                        try:
                            handler(event, db)
                        except Exception as e:
                            logger.error("Error processing %s event: %s", event_name, e)
            finally:
                db.close()

            from_block = current_block + 1
            last_block_file.write_text(str(from_block))

        except Exception as e:
            logger.error("Listener error: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_listener()
