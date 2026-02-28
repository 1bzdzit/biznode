"""
Tests for identity/wallet.py
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_generate_wallet_creates_files(tmp_path, monkeypatch):
    """generate_wallet() must create wallet_address.txt and wallet_key.enc."""
    import identity.wallet as w_mod
    from pathlib import Path

    monkeypatch.setattr(w_mod, "WALLET_ADDRESS_FILE", tmp_path / "wallet_address.txt")
    monkeypatch.setattr(w_mod, "WALLET_KEY_ENC_FILE", tmp_path / "wallet_key.enc")

    addr = w_mod.generate_wallet(b"test-password")

    assert (tmp_path / "wallet_address.txt").exists()
    assert (tmp_path / "wallet_key.enc").exists()
    assert addr.startswith("0x")
    assert len(addr) == 42


def test_wallet_address_is_valid_ethereum(tmp_path, monkeypatch):
    """Generated address must be a valid Ethereum checksum address."""
    import identity.wallet as w_mod
    from eth_account import Account

    monkeypatch.setattr(w_mod, "WALLET_ADDRESS_FILE", tmp_path / "wallet_address.txt")
    monkeypatch.setattr(w_mod, "WALLET_KEY_ENC_FILE", tmp_path / "wallet_key.enc")

    addr = w_mod.generate_wallet(b"test-password")
    # eth_account.Account.is_checksum_address validates EIP-55 checksum
    assert Account.is_checksum_address(addr)


def test_load_wallet_address(tmp_path, monkeypatch):
    """load_wallet_address() returns the stored address."""
    import identity.wallet as w_mod

    monkeypatch.setattr(w_mod, "WALLET_ADDRESS_FILE", tmp_path / "wallet_address.txt")
    monkeypatch.setattr(w_mod, "WALLET_KEY_ENC_FILE", tmp_path / "wallet_key.enc")

    addr = w_mod.generate_wallet(b"test-password")
    assert w_mod.load_wallet_address() == addr


def test_load_private_key_roundtrip(tmp_path, monkeypatch):
    """load_private_key() must decrypt and return the original private key."""
    import identity.wallet as w_mod
    from eth_account import Account

    monkeypatch.setattr(w_mod, "WALLET_ADDRESS_FILE", tmp_path / "wallet_address.txt")
    monkeypatch.setattr(w_mod, "WALLET_KEY_ENC_FILE", tmp_path / "wallet_key.enc")

    addr = w_mod.generate_wallet(b"test-password")
    pk_hex = w_mod.load_private_key(b"test-password")

    # Verify the private key corresponds to the generated address
    recovered = Account.from_key(pk_hex)
    assert recovered.address == addr


def test_wrong_password_raises_value_error(tmp_path, monkeypatch):
    """load_private_key() raises ValueError on wrong password."""
    import identity.wallet as w_mod

    monkeypatch.setattr(w_mod, "WALLET_ADDRESS_FILE", tmp_path / "wallet_address.txt")
    monkeypatch.setattr(w_mod, "WALLET_KEY_ENC_FILE", tmp_path / "wallet_key.enc")

    w_mod.generate_wallet(b"correct-password")

    with pytest.raises(ValueError, match="Incorrect password"):
        w_mod.load_private_key(b"wrong-password")


def test_generate_wallet_raises_if_exists(tmp_path, monkeypatch):
    """generate_wallet() raises FileExistsError if wallet already exists."""
    import identity.wallet as w_mod

    monkeypatch.setattr(w_mod, "WALLET_ADDRESS_FILE", tmp_path / "wallet_address.txt")
    monkeypatch.setattr(w_mod, "WALLET_KEY_ENC_FILE", tmp_path / "wallet_key.enc")

    w_mod.generate_wallet(b"test-password")

    with pytest.raises(FileExistsError):
        w_mod.generate_wallet(b"test-password")


def test_wallet_exists_false_when_missing(tmp_path, monkeypatch):
    """wallet_exists() returns False when no wallet files are present."""
    import identity.wallet as w_mod

    monkeypatch.setattr(w_mod, "WALLET_ADDRESS_FILE", tmp_path / "wallet_address.txt")
    monkeypatch.setattr(w_mod, "WALLET_KEY_ENC_FILE", tmp_path / "wallet_key.enc")

    assert w_mod.wallet_exists() is False
