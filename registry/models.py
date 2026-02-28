"""
Registry Data Models
====================
SQLAlchemy ORM models for the off-chain BizNode registry database.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Float, Integer, DateTime, Text, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class NodeRecord(Base):
    """Extended off-chain metadata for a registered BizNode."""

    __tablename__ = "nodes"

    # Primary key — matches on-chain nodeHash (hex string)
    node_hash   = Column(String(66), primary_key=True)  # 0x + 64 hex chars

    # Identity
    node_id     = Column(String(64), unique=True, nullable=False)  # SHA-256 hex
    public_key  = Column(Text, nullable=True)   # PEM-encoded Ed25519 public key
    wallet      = Column(String(42), nullable=True)  # Ethereum address

    # DNS
    dns_name    = Column(String(128), unique=True, nullable=True)  # e.g. shashi.1bz

    # On-chain sync
    verified    = Column(Boolean, default=False)
    stake_wei   = Column(String(32), default="0")  # Store as string to avoid overflow
    registered_at = Column(DateTime, nullable=True)

    # Off-chain trust scoring
    trust_score     = Column(Float, default=0.0)
    uptime_score    = Column(Float, default=0.0)
    ai_quality_score = Column(Float, default=0.0)
    complaint_count = Column(Integer, default=0)
    endorsement_count = Column(Integer, default=0)
    trust_tier      = Column(String(20), default="UNVERIFIED")

    # Metadata
    ip_address  = Column(String(45), nullable=True)
    last_seen   = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active      = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "node_hash":        self.node_hash,
            "node_id":          self.node_id,
            "wallet":           self.wallet,
            "dns_name":         self.dns_name,
            "verified":         self.verified,
            "stake_wei":        self.stake_wei,
            "trust_score":      self.trust_score,
            "trust_tier":       self.trust_tier,
            "ip_address":       self.ip_address,
            "last_seen":        self.last_seen.isoformat() if self.last_seen else None,
            "registered_at":    self.registered_at.isoformat() if self.registered_at else None,
            "active":           self.active,
        }


# ── Database setup ────────────────────────────────────────────────────────────

DATABASE_URL = "sqlite:///registry/biznode_registry.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
