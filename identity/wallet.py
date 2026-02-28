"""
BizNode Wallet Module
=====================
Generates and manages a Polygon/Ethereum wallet for each node.

The wallet private key is encrypted at rest using Fernet symmetric
encryption derived from the node password. Only the public wallet
address is stored in plaintext.

Dependencies:
    pip install web3 eth-account cryptography
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent

WALLET_ADDRESS_FILE = BASE_DIR / "wallet_address.txt"
WALLET_KEY_ENC_FILE = BASE_DIR / "wallet_key.enc"


def _derive_fernet_key(password: bytes) -> bytes:
    """Derive a 32-byte Fernet-compatible key from the node password."""
    import hashlib, base64
    raw = hashlib.sha256(password).digest()
    return base64.urlsafe_b64encode(raw)


def generate_wallet(password: bytes) -> str:
    """Generate a new Ethereum/Polygon wallet and store it encrypted.

    Args:
        password: The node password bytes used to encrypt the private key.

    Returns:
        wallet_address: The public Ethereum address (0x...).

    Raises:
        ImportError: If web3 or eth-account is not installed.
        FileExistsError: If a wallet already exists.
    """
    if wallet_exists():
        raise FileExistsError(
            "Wallet already exists. Delete wallet_key.enc and wallet_address.txt to regenerate."
        )

    try:
        from eth_account import Account
        from cryptography.fernet import Fernet
    except ImportError as e:
        raise ImportError(
            f"Missing dependency: {e}. Run: pip install web3 eth-account cryptography"
        ) from e

    acct = Account.create()
    address = acct.address
    private_key_hex = acct.key.hex()

    # Encrypt private key
    fernet_key = _derive_fernet_key(password)
    f = Fernet(fernet_key)
    encrypted = f.encrypt(private_key_hex.encode())

    WALLET_KEY_ENC_FILE.write_bytes(encrypted)
    WALLET_ADDRESS_FILE.write_text(address)

    logger.info("Wallet generated. address=%s", address)
    return address


def load_wallet_address() -> str:
    """Return the stored public wallet address."""
    if not WALLET_ADDRESS_FILE.exists():
        raise FileNotFoundError(
            "wallet_address.txt not found. Run generate_wallet() first."
        )
    return WALLET_ADDRESS_FILE.read_text().strip()


def load_private_key(password: bytes) -> str:
    """Decrypt and return the private key hex string.

    WARNING: Handle the returned value with care — never log or expose it.
    """
    if not WALLET_KEY_ENC_FILE.exists():
        raise FileNotFoundError(
            "wallet_key.enc not found. Run generate_wallet() first."
        )

    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError as e:
        raise ImportError(f"Missing dependency: {e}") from e

    fernet_key = _derive_fernet_key(password)
    f = Fernet(fernet_key)
    try:
        decrypted = f.decrypt(WALLET_KEY_ENC_FILE.read_bytes())
    except InvalidToken:
        raise ValueError("Incorrect password — cannot decrypt wallet private key.")

    return decrypted.decode()


def wallet_exists() -> bool:
    """Return True if both wallet files are present."""
    return WALLET_ADDRESS_FILE.exists() and WALLET_KEY_ENC_FILE.exists()


def get_node_hash(node_id: str) -> bytes:
    """Compute keccak256(node_id) for use as the on-chain nodeHash.

    Args:
        node_id: The hex string node_id from identity.py.

    Returns:
        32-byte keccak256 digest.
    """
    try:
        from web3 import Web3
    except ImportError as e:
        raise ImportError(f"Missing dependency: {e}. Run: pip install web3") from e

    return Web3.keccak(text=node_id)


if __name__ == "__main__":
    import getpass
    pwd = getpass.getpass("Enter node password to generate wallet: ").encode()
    addr = generate_wallet(pwd)
    print(f"Wallet address: {addr}")
    print(f"Stored encrypted key: {WALLET_KEY_ENC_FILE}")
