"""Test F08: Verify TODO(audit-F08) comments exist on Decimal("0") fee params."""
import ast
import pathlib


def test_fee_todo_documented():
    """All Decimal("0") fee parameters in manager.py should have TODO comment."""
    manager_path = pathlib.Path(__file__).resolve().parents[1] / (
        "packages/sardis-wallet/src/sardis_wallet/manager.py"
    )
    source = manager_path.read_text()
    lines = source.splitlines()

    # Find all lines with Decimal("0")
    decimal_zero_lines = [
        (i + 1, line) for i, line in enumerate(lines) if 'Decimal("0")' in line
    ]

    assert len(decimal_zero_lines) >= 3, (
        f"Expected at least 3 Decimal('0') occurrences, found {len(decimal_zero_lines)}"
    )

    for lineno, line in decimal_zero_lines:
        assert "TODO(audit-F08)" in line, (
            f"Line {lineno} has Decimal('0') without TODO(audit-F08) comment: {line.strip()}"
        )
