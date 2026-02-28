"""
BizNodeRegistry Contract Deployment Script
==========================================
Deploys BizNodeRegistry.sol to Polygon (or Mumbai testnet).

Prerequisites:
    pip install web3 py-solc-x

Usage:
    python contracts/deploy.py

Environment variables (set in .env):
    POLYGON_RPC_URL   - RPC endpoint (e.g. https://polygon-rpc.com)
    WALLET_PRIVATE_KEY - Deployer private key (hex, no 0x prefix)
"""

import os
import json
import sys
from pathlib import Path

# ── Load environment ──────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # dotenv optional

RPC_URL     = os.getenv("POLYGON_RPC_URL", "https://rpc-mumbai.maticvigil.com")
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")

if not PRIVATE_KEY:
    print("ERROR: WALLET_PRIVATE_KEY not set in .env")
    sys.exit(1)

# ── Compile contract ──────────────────────────────────────────────────────────
def compile_contract():
    """Compile BizNodeRegistry.sol using py-solc-x."""
    try:
        from solcx import compile_source, install_solc
    except ImportError:
        print("ERROR: py-solc-x not installed. Run: pip install py-solc-x")
        sys.exit(1)

    install_solc("0.8.20")

    sol_path = Path(__file__).parent / "BizNodeRegistry.sol"
    source = sol_path.read_text()

    compiled = compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version="0.8.20",
    )

    contract_id = "<stdin>:BizNodeRegistry"
    return compiled[contract_id]["abi"], compiled[contract_id]["bin"]


# ── Deploy ────────────────────────────────────────────────────────────────────
def deploy():
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to RPC: {RPC_URL}")
        sys.exit(1)

    account = w3.eth.account.from_key(PRIVATE_KEY)
    print(f"Deployer address : {account.address}")
    print(f"Network          : {RPC_URL}")
    print(f"Balance          : {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} MATIC")

    abi, bytecode = compile_contract()

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    tx = Contract.constructor().build_transaction({
        "from":     account.address,
        "nonce":    nonce,
        "gas":      2_000_000,
        "gasPrice": gas_price,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"Deploying... tx hash: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    contract_address = receipt.contractAddress

    print(f"\n✅ BizNodeRegistry deployed at: {contract_address}")
    print(f"   Block: {receipt.blockNumber}")
    print(f"   Gas used: {receipt.gasUsed}")

    # Save ABI and address for registry use
    abi_path = Path(__file__).parent / "abi.json"
    abi_path.write_text(json.dumps(abi, indent=2))
    print(f"\nABI saved to: {abi_path}")

    # Update config
    config_path = Path(__file__).parent.parent / "config" / "node_config.yaml"
    if config_path.exists():
        content = config_path.read_text()
        content = content.replace(
            'contract_address: ""',
            f'contract_address: "{contract_address}"'
        )
        config_path.write_text(content)
        print(f"Updated contract_address in {config_path}")

    return contract_address


if __name__ == "__main__":
    deploy()
