"""
1bz DNS Resolver
================
Resolves human-readable 1bz domain names to node metadata.

Resolution flow:
  1. Query BizNodeRegistry smart contract resolveDNS(dnsName) → nodeHash
  2. Fetch extended metadata from off-chain registry DB
  3. Return: wallet, public_key, ip_address, trust_score, trust_tier, verified

This module can be used:
  - As a library by the FastAPI registry
  - As a standalone REST resolver
  - As a basis for a browser plugin or custom gateway
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)

RPC_URL          = os.getenv("POLYGON_RPC_URL",  "https://polygon-rpc.com")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
ABI_PATH         = Path(__file__).parent.parent / "contracts" / "abi.json"


@dataclass
class DNSRecord:
    """Resolved DNS record for a 1bz domain name."""
    dns_name:    str
    node_hash:   str
    wallet:      Optional[str]
    public_key:  Optional[str]
    ip_address:  Optional[str]
    trust_score: float
    trust_tier:  str
    verified:    bool
    active:      bool

    def to_dict(self) -> dict:
        return asdict(self)


class BizNodeDNSResolver:
    """Resolves 1bz domain names using on-chain + off-chain data."""

    def __init__(self, db_session=None):
        self._db = db_session
        self._w3 = None
        self._contract = None

    def _get_web3(self):
        if self._w3 is None:
            try:
                from web3 import Web3
                self._w3 = Web3(Web3.HTTPProvider(RPC_URL))
            except ImportError:
                raise ImportError("web3 not installed. Run: pip install web3")
        return self._w3

    def _get_contract(self):
        if self._contract is None:
            if not CONTRACT_ADDRESS:
                raise ValueError("CONTRACT_ADDRESS not set.")
            w3 = self._get_web3()
            abi = json.loads(ABI_PATH.read_text())
            self._contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)
        return self._contract

    def resolve_on_chain(self, dns_name: str) -> Optional[str]:
        """Query the smart contract to get nodeHash for a DNS name.

        Returns:
            nodeHash as hex string (0x...), or None if not found.
        """
        try:
            contract = self._get_contract()
            node_hash_bytes = contract.functions.resolveDNS(dns_name).call()
            if node_hash_bytes == b"\x00" * 32:
                return None
            return "0x" + node_hash_bytes.hex()
        except Exception as e:
            logger.warning("On-chain DNS resolution failed for '%s': %s", dns_name, e)
            return None

    def resolve_off_chain(self, node_hash: str) -> Optional[dict]:
        """Fetch extended metadata from the off-chain registry DB.

        Returns:
            dict with node metadata, or None if not found.
        """
        if not self._db:
            return None
        try:
            from registry.models import NodeRecord
            node = self._db.query(NodeRecord).filter_by(node_hash=node_hash).first()
            if node:
                return node.to_dict()
        except Exception as e:
            logger.warning("Off-chain lookup failed for %s: %s", node_hash, e)
        return None

    def resolve(self, dns_name: str) -> Optional[DNSRecord]:
        """Full resolution: on-chain → off-chain → DNSRecord.

        Args:
            dns_name: e.g. "shashi.1bz"

        Returns:
            DNSRecord if found, None otherwise.
        """
        # Step 1: On-chain lookup
        node_hash = self.resolve_on_chain(dns_name)
        if not node_hash:
            logger.info("DNS not found on-chain: %s", dns_name)
            return None

        # Step 2: Off-chain metadata
        meta = self.resolve_off_chain(node_hash)

        if meta:
            return DNSRecord(
                dns_name    = dns_name,
                node_hash   = node_hash,
                wallet      = meta.get("wallet"),
                public_key  = meta.get("public_key"),
                ip_address  = meta.get("ip_address"),
                trust_score = meta.get("trust_score", 0.0),
                trust_tier  = meta.get("trust_tier", "UNVERIFIED"),
                verified    = meta.get("verified", False),
                active      = meta.get("active", True),
            )

        # Fallback: on-chain data only
        try:
            contract = self._get_contract()
            from web3 import Web3
            node_hash_bytes = bytes.fromhex(node_hash[2:])
            on_chain = contract.functions.getNode(node_hash_bytes).call()
            return DNSRecord(
                dns_name    = dns_name,
                node_hash   = node_hash,
                wallet      = on_chain[0],
                public_key  = None,
                ip_address  = None,
                trust_score = 0.0,
                trust_tier  = "VERIFIED" if on_chain[2] else "UNVERIFIED",
                verified    = on_chain[2],
                active      = on_chain[5],
            )
        except Exception as e:
            logger.warning("On-chain getNode failed: %s", e)
            return None

    def reverse_lookup(self, node_hash: str) -> Optional[str]:
        """Return the DNS name for a given nodeHash (off-chain lookup).

        Args:
            node_hash: hex string (0x...)

        Returns:
            dns_name string or None.
        """
        if not self._db:
            return None
        try:
            from registry.models import NodeRecord
            node = self._db.query(NodeRecord).filter_by(node_hash=node_hash).first()
            return node.dns_name if node else None
        except Exception as e:
            logger.warning("Reverse lookup failed: %s", e)
            return None
