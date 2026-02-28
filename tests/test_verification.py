"""
Tests for core/verification.py
"""
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.verification import check_verification


def test_local_mode_returns_unverified():
    """In local mode, verification always returns UNVERIFIED."""
    config = {"mode": "local"}
    assert check_verification(config) == "UNVERIFIED"


def test_missing_mode_defaults_to_unverified():
    """Missing mode key defaults to UNVERIFIED."""
    assert check_verification({}) == "UNVERIFIED"


def test_registry_mode_returns_status_from_api():
    """In registry mode, returns the status from the registry API."""
    config = {
        "mode": "registry",
        "entity_slug": "testnode",
        "registry_api": "https://registry.1bz.io/verify",
    }
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "VERIFIED"}

    with patch("core.verification.requests.get", return_value=mock_response):
        result = check_verification(config)

    assert result == "VERIFIED"


def test_registry_mode_returns_unverified_on_network_error():
    """In registry mode, returns UNVERIFIED if the API call fails."""
    config = {
        "mode": "registry",
        "entity_slug": "testnode",
        "registry_api": "https://registry.1bz.io/verify",
    }
    with patch("core.verification.requests.get", side_effect=Exception("timeout")):
        result = check_verification(config)

    assert result == "UNVERIFIED"


def test_registry_mode_missing_slug_returns_unverified():
    """In registry mode, missing entity_slug returns UNVERIFIED."""
    config = {"mode": "registry", "registry_api": "https://registry.1bz.io/verify"}
    result = check_verification(config)
    assert result == "UNVERIFIED"
