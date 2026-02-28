"""
Trust Scoring Engine
====================
Computes a dynamic trust score for each BizNode based on multiple signals.

Trust score formula (0.0 – 100.0):
    score = (
        stake_weight    * 30  +
        uptime_weight   * 25  +
        ai_quality      * 20  +
        endorsements    * 15  +
        complaint_ratio * -10 +
        verified_bonus  * 10
    )

Tier mapping:
    90–100 → ENTERPRISE
    70–89  → TRUSTED
    40–69  → VERIFIED (if on-chain verified)
    1–39   → UNVERIFIED
    0      → UNVERIFIED
"""

import math
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Weights ───────────────────────────────────────────────────────────────────
STAKE_WEIGHT       = 30.0
UPTIME_WEIGHT      = 25.0
AI_QUALITY_WEIGHT  = 20.0
ENDORSEMENT_WEIGHT = 15.0
COMPLAINT_PENALTY  = 10.0
VERIFIED_BONUS     = 10.0

# Maximum stake considered for full score (in MATIC)
MAX_STAKE_MATIC = 1000.0


@dataclass
class TrustInputs:
    stake_matic:       float = 0.0   # Total staked MATIC
    uptime_ratio:      float = 0.0   # 0.0 – 1.0 (fraction of time online)
    ai_quality_score:  float = 0.0   # 0.0 – 1.0 (response quality rating)
    endorsement_count: int   = 0     # Number of peer endorsements
    complaint_count:   int   = 0     # Number of complaints received
    total_interactions: int  = 1     # Total interactions (for complaint ratio)
    verified:          bool  = False # On-chain verified flag


def compute_trust_score(inputs: TrustInputs) -> tuple[float, str]:
    """Compute trust score and tier from TrustInputs.

    Returns:
        (score: float 0–100, tier: str)
    """
    # Stake component: logarithmic scaling up to MAX_STAKE_MATIC
    if inputs.stake_matic > 0:
        stake_norm = min(math.log1p(inputs.stake_matic) / math.log1p(MAX_STAKE_MATIC), 1.0)
    else:
        stake_norm = 0.0

    # Uptime component
    uptime_norm = max(0.0, min(1.0, inputs.uptime_ratio))

    # AI quality component
    ai_norm = max(0.0, min(1.0, inputs.ai_quality_score))

    # Endorsement component: logarithmic scaling
    endorsement_norm = min(math.log1p(inputs.endorsement_count) / math.log1p(100), 1.0)

    # Complaint ratio penalty
    if inputs.total_interactions > 0:
        complaint_ratio = inputs.complaint_count / inputs.total_interactions
    else:
        complaint_ratio = 0.0
    complaint_penalty = min(complaint_ratio * COMPLAINT_PENALTY, COMPLAINT_PENALTY)

    # Verified bonus
    verified_bonus = VERIFIED_BONUS if inputs.verified else 0.0

    score = (
        stake_norm       * STAKE_WEIGHT
        + uptime_norm    * UPTIME_WEIGHT
        + ai_norm        * AI_QUALITY_WEIGHT
        + endorsement_norm * ENDORSEMENT_WEIGHT
        - complaint_penalty
        + verified_bonus
    )

    score = max(0.0, min(100.0, score))

    tier = _score_to_tier(score, inputs.verified)

    logger.debug(
        "Trust score computed: %.2f (%s) | stake=%.2f uptime=%.2f ai=%.2f "
        "endorsements=%d complaints=%d verified=%s",
        score, tier,
        inputs.stake_matic, inputs.uptime_ratio, inputs.ai_quality_score,
        inputs.endorsement_count, inputs.complaint_count, inputs.verified,
    )

    return round(score, 2), tier


def _score_to_tier(score: float, verified: bool) -> str:
    if score >= 90:
        return "ENTERPRISE"
    if score >= 70:
        return "TRUSTED"
    if score >= 40 and verified:
        return "VERIFIED"
    return "UNVERIFIED"


def update_node_trust(db_session, node_hash: str) -> tuple[float, str]:
    """Recompute and persist trust score for a node in the database.

    Args:
        db_session: SQLAlchemy session.
        node_hash:  The node's on-chain hash (hex string).

    Returns:
        (score, tier)
    """
    from registry.models import NodeRecord
    from web3 import Web3

    node = db_session.query(NodeRecord).filter_by(node_hash=node_hash).first()
    if not node:
        raise ValueError(f"Node {node_hash} not found in registry.")

    stake_matic = float(Web3.from_wei(int(node.stake_wei or 0), "ether"))

    inputs = TrustInputs(
        stake_matic        = stake_matic,
        uptime_ratio       = node.uptime_score,
        ai_quality_score   = node.ai_quality_score,
        endorsement_count  = node.endorsement_count,
        complaint_count    = node.complaint_count,
        total_interactions = max(1, node.endorsement_count + node.complaint_count),
        verified           = node.verified,
    )

    score, tier = compute_trust_score(inputs)

    node.trust_score = score
    node.trust_tier  = tier
    db_session.commit()

    return score, tier
