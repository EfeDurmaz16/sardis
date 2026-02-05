"""Test F03: Wallet manager should not silently fall back to /100 on unknown tokens."""
import pytest
from sardis_v2_core.tokens import normalize_token_amount


def test_wallet_no_silent_fallback():
    """Unknown token should raise ValueError, not silently use /100."""
    with pytest.raises((ValueError, KeyError)):
        normalize_token_amount("UNKNOWN_TOKEN", 1000)
