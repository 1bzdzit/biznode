"""
Tests for core/badge.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.badge import get_badge


def test_verified_badge():
    assert get_badge("VERIFIED") == "🔵 1BZ VERIFIED"


def test_trusted_badge():
    assert get_badge("TRUSTED") == "🟢 1BZ TRUSTED NODE"


def test_enterprise_badge():
    assert get_badge("ENTERPRISE") == "🟣 1BZ ENTERPRISE"


def test_unverified_badge():
    assert get_badge("UNVERIFIED") == "🟡 SELF DECLARED"


def test_unknown_status_defaults_to_self_declared():
    """Any unknown status should fall back to SELF DECLARED."""
    assert get_badge("UNKNOWN_STATUS") == "🟡 SELF DECLARED"
    assert get_badge("") == "🟡 SELF DECLARED"
    assert get_badge(None) == "🟡 SELF DECLARED"
