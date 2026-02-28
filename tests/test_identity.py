"""
Tests for identity/identity.py
"""
import os
import sys
import tempfile
import pytest

# Allow importing from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_generate_identity_creates_all_files(tmp_path, monkeypatch):
    """generate_identity() must create all three identity files."""
    import identity.identity as id_mod

    monkeypatch.setattr(id_mod, "BASE_DIR", str(tmp_path))

    node_id = id_mod.generate_identity(b"test-password")

    assert (tmp_path / "node_private.pem").exists(), "node_private.pem missing"
    assert (tmp_path / "node_public.pem").exists(), "node_public.pem missing"
    assert (tmp_path / "node_id.txt").exists(), "node_id.txt missing"
    assert len(node_id) == 64, "node_id should be 64-char hex (SHA-256)"


def test_node_id_is_sha256_of_public_key(tmp_path, monkeypatch):
    """node_id must equal SHA-256 of the PEM-encoded public key."""
    import hashlib
    import identity.identity as id_mod

    monkeypatch.setattr(id_mod, "BASE_DIR", str(tmp_path))
    node_id = id_mod.generate_identity(b"test-password")

    pub_bytes = (tmp_path / "node_public.pem").read_bytes()
    expected = hashlib.sha256(pub_bytes).hexdigest()
    assert node_id == expected


def test_identity_exists_returns_false_when_missing(tmp_path, monkeypatch):
    """identity_exists() returns False when no files are present."""
    import identity.identity as id_mod

    monkeypatch.setattr(id_mod, "BASE_DIR", str(tmp_path))
    assert id_mod.identity_exists() is False


def test_identity_exists_returns_true_after_generation(tmp_path, monkeypatch):
    """identity_exists() returns True only after all three files are created."""
    import identity.identity as id_mod

    monkeypatch.setattr(id_mod, "BASE_DIR", str(tmp_path))
    id_mod.generate_identity(b"test-password")
    assert id_mod.identity_exists() is True


def test_identity_exists_false_if_partial(tmp_path, monkeypatch):
    """identity_exists() returns False if only some files are present."""
    import identity.identity as id_mod

    monkeypatch.setattr(id_mod, "BASE_DIR", str(tmp_path))
    id_mod.generate_identity(b"test-password")

    # Remove one file to simulate partial corruption
    (tmp_path / "node_id.txt").unlink()
    assert id_mod.identity_exists() is False


def test_load_node_id(tmp_path, monkeypatch):
    """load_node_id() returns the stored node_id string."""
    import identity.identity as id_mod

    monkeypatch.setattr(id_mod, "BASE_DIR", str(tmp_path))
    node_id = id_mod.generate_identity(b"test-password")
    assert id_mod.load_node_id() == node_id


def test_load_node_id_raises_when_missing(tmp_path, monkeypatch):
    """load_node_id() raises FileNotFoundError when node_id.txt is absent."""
    import identity.identity as id_mod

    monkeypatch.setattr(id_mod, "BASE_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        id_mod.load_node_id()
