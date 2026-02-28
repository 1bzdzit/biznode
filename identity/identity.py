import os
import hashlib
import logging
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)

IDENTITY_FILES = ["node_private.pem", "node_public.pem", "node_id.txt"]


def generate_identity(password: bytes) -> str:
    """Generate a new Ed25519 keypair and derive node_id from the public key.

    Args:
        password: Bytes used to encrypt the private key at rest.

    Returns:
        node_id: SHA-256 hex digest of the PEM-encoded public key.
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )

    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(os.path.join(BASE_DIR, "node_private.pem"), "wb") as f:
        f.write(priv_bytes)

    with open(os.path.join(BASE_DIR, "node_public.pem"), "wb") as f:
        f.write(pub_bytes)

    node_id = hashlib.sha256(pub_bytes).hexdigest()

    with open(os.path.join(BASE_DIR, "node_id.txt"), "w") as f:
        f.write(node_id)

    logger.info("Identity generated. node_id=%s", node_id)
    return node_id


def identity_exists() -> bool:
    """Return True only when ALL three identity files are present.

    Checking only the private key is insufficient — a partial write
    (e.g. power loss) could leave the identity in a corrupt state.
    """
    return all(
        os.path.exists(os.path.join(BASE_DIR, fname)) for fname in IDENTITY_FILES
    )


def load_node_id() -> str:
    """Read and return the stored node_id string."""
    path = os.path.join(BASE_DIR, "node_id.txt")
    if not os.path.exists(path):
        raise FileNotFoundError("node_id.txt not found. Run generate_identity() first.")
    with open(path) as f:
        return f.read().strip()


def load_public_key_pem() -> bytes:
    """Return the raw PEM bytes of the node public key."""
    path = os.path.join(BASE_DIR, "node_public.pem")
    with open(path, "rb") as f:
        return f.read()
