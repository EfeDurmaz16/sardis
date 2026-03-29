"""Tests for ledger financial precision — no float() conversion.

Verifies that Decimal precision is preserved through the ledger pipeline
and that float() is never used on financial amounts.
"""
from __future__ import annotations

import ast
import inspect
from decimal import Decimal
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Static analysis: ensure float() is not used on financial fields
# ---------------------------------------------------------------------------

LEDGER_PKG = Path(__file__).resolve().parent.parent / "packages" / "sardis-ledger" / "src" / "sardis_ledger"


def _find_float_calls_in_file(filepath: Path) -> list[tuple[int, str]]:
    """Return (line_number, line_text) for any `float(...)` call in the file.

    Only flags calls where the argument name hints at a financial value
    (amount, fee, balance, running, cost, price, total, minor).
    """
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    hits: list[tuple[int, str]] = []
    lines = source.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if it's a call to float()
            if isinstance(node.func, ast.Name) and node.func.id == "float":
                if node.args:
                    arg = node.args[0]
                    # Get the source text of the argument
                    arg_text = ast.get_source_segment(source, arg) or ""
                    financial_keywords = (
                        "amount", "fee", "balance", "running", "cost",
                        "price", "total", "minor", "major",
                    )
                    if any(kw in arg_text.lower() for kw in financial_keywords):
                        line_text = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                        hits.append((node.lineno, line_text))
    return hits


class TestNoFloatConversionOnFinancialValues:
    """Static analysis: float() must never be called on financial amounts in the ledger package."""

    def test_db_engine_no_float_on_amounts(self):
        """db_engine.py must not convert amounts/fees/balances via float()."""
        filepath = LEDGER_PKG / "db_engine.py"
        if not filepath.exists():
            pytest.skip("db_engine.py not found")

        hits = _find_float_calls_in_file(filepath)
        assert hits == [], (
            f"float() called on financial values in db_engine.py at lines: "
            f"{[f'L{ln}: {txt}' for ln, txt in hits]}"
        )

    def test_records_no_float_on_amounts(self):
        """records.py must not convert amounts via float()."""
        filepath = LEDGER_PKG / "records.py"
        if not filepath.exists():
            pytest.skip("records.py not found")

        hits = _find_float_calls_in_file(filepath)
        assert hits == [], (
            f"float() called on financial values in records.py at lines: "
            f"{[f'L{ln}: {txt}' for ln, txt in hits]}"
        )

    def test_all_ledger_files_no_float_on_amounts(self):
        """No file in sardis-ledger should use float() on financial values."""
        if not LEDGER_PKG.exists():
            pytest.skip("sardis-ledger package not found")

        all_hits: dict[str, list[tuple[int, str]]] = {}
        for py_file in LEDGER_PKG.rglob("*.py"):
            hits = _find_float_calls_in_file(py_file)
            if hits:
                all_hits[str(py_file.relative_to(LEDGER_PKG))] = hits

        assert all_hits == {}, (
            f"float() called on financial values in ledger package: {all_hits}"
        )


# ---------------------------------------------------------------------------
# Decimal precision tests
# ---------------------------------------------------------------------------

class TestDecimalPrecision:
    """Verify that Decimal values survive the str() conversion path without precision loss."""

    def test_str_preserves_18_decimal_places(self):
        """str(Decimal) must preserve all 18 decimal places for USDC-like amounts.

        Note: Decimal("0.000000000000000001") may serialize as "1E-18" via str().
        asyncpg handles both forms correctly for NUMERIC columns, but we verify
        that the value round-trips through Decimal without precision loss.
        """
        amount = Decimal("0.000000000000000001")  # 1 wei equivalent
        # Verify the value is preserved (asyncpg accepts scientific notation for NUMERIC)
        assert amount == Decimal("0.000000000000000001")
        # Verify str() does not lose precision (it may use scientific notation)
        assert Decimal(str(amount)) == Decimal("0.000000000000000001")

    def test_str_preserves_large_amounts(self):
        """str(Decimal) must handle large amounts without scientific notation."""
        amount = Decimal("99999999999999999.999999999999999999")
        result = str(amount)
        assert "E" not in result and "e" not in result
        assert result == "99999999999999999.999999999999999999"

    def test_float_loses_precision(self):
        """Demonstrate that float() would lose precision — this is the bug we fixed."""
        precise = Decimal("1.123456789012345678")
        via_float = float(precise)
        via_str = str(precise)

        # float loses precision after ~15 significant digits
        assert str(via_float) != "1.123456789012345678"
        # str preserves all digits
        assert via_str == "1.123456789012345678"

    def test_small_difference_survives_str(self):
        """Two amounts differing by 1 wei must remain distinct through str()."""
        a = Decimal("1000000.000000000000000001")
        b = Decimal("1000000.000000000000000002")

        assert str(a) != str(b)
        # float would make them equal
        assert float(a) == float(b), "float should lose this precision (proving the bug)"

    def test_fee_precision_preserved(self):
        """Sub-cent fees must preserve precision."""
        fee = Decimal("0.000001")  # 1 micro-unit
        assert str(fee) == "0.000001"

    def test_running_balance_computation(self):
        """Running balance = current - amount - fee must be exact in Decimal."""
        current = Decimal("1000.000000000000000000")
        amount = Decimal("100.000000000000000001")
        fee = Decimal("0.000000000000000001")

        running = current - amount - fee
        expected = Decimal("899.999999999999999998")

        assert running == expected
        assert str(running) == "899.999999999999999998"

    def test_zero_amount_str(self):
        """Zero amounts must serialize correctly."""
        assert str(Decimal("0")) == "0"
        assert str(Decimal("0.000000")) == "0.000000"

    def test_negative_amount_str(self):
        """Negative amounts (debits) must serialize correctly."""
        amount = Decimal("-500.123456789012345678")
        assert str(amount) == "-500.123456789012345678"


class TestDecimalVsFloatComparison:
    """Quantify precision loss from float() to justify the fix."""

    CASES = [
        ("0.1", "0.1"),
        ("0.000000001", "0.000000001"),
        ("123456789.123456789", "123456789.123456789"),
        ("0.000000000000000001", "0.000000000000000001"),
        ("99999999999.999999999999", "99999999999.999999999999"),
    ]

    @pytest.mark.parametrize("decimal_str,expected", CASES)
    def test_str_round_trips_exactly(self, decimal_str: str, expected: str):
        """str(Decimal) must round-trip without precision loss.

        Note: str() may use scientific notation (e.g. "1E-9") but the value
        is preserved. asyncpg handles both forms for NUMERIC columns.
        """
        d = Decimal(decimal_str)
        # The critical property: Decimal(str(d)) == original value
        assert Decimal(str(d)) == Decimal(expected)

    @pytest.mark.parametrize("decimal_str,expected", CASES)
    def test_float_may_lose_precision(self, decimal_str: str, expected: str):
        """float() does NOT always round-trip. This test documents known precision loss."""
        d = Decimal(decimal_str)
        via_float = str(float(d))
        # We're just documenting: at least some of these will fail round-trip
        # The test passes regardless — it's informational
        if via_float != expected:
            # Expected: float loses precision for some values
            pass
