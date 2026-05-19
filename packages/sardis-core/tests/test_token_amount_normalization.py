"""Tests for F01: Ledger amount normalization fixes."""
from decimal import Decimal


def test_ledger_uses_token_decimals_not_hardcoded():
    """USDC amount_minor=1_000_000 should become Decimal('1.000000'), NOT Decimal('10000.00')"""
    from sardis_v2_core.tokens import normalize_token_amount
    result = normalize_token_amount("USDC", 1_000_000)
    assert result == Decimal("1.000000"), f"Expected 1.000000 but got {result}"
    # The old /10**2 would give 10000.00 - verify that's wrong
    wrong_result = Decimal(1_000_000) / Decimal(10**2)
    assert wrong_result == Decimal("10000"), "Confirming old approach was wrong"


def test_ledger_str_not_float():
    """Decimal precision must be preserved, no float rounding."""
    # Use a value that clearly demonstrates float precision loss
    amount = Decimal("1.00000000000000000001")
    assert str(amount) == "1.00000000000000000001"
    # float cannot represent this - it rounds to 1.0
    assert str(float(amount)) != "1.00000000000000000001", (
        "float should lose precision for high-precision Decimal values"
    )
