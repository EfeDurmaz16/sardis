"""Test F08: Verify gas fee estimates are defined in manager.py."""
import pathlib


def test_gas_fee_estimates_defined():
    """Gas fee estimates should be defined for supported chains in manager.py."""
    manager_path = pathlib.Path(__file__).resolve().parents[1] / (
        "packages/sardis-wallet/src/sardis_wallet/manager.py"
    )
    source = manager_path.read_text()

    # Verify the gas fee estimates dict exists
    assert "_GAS_FEE_ESTIMATES_USD" in source, (
        "manager.py must define _GAS_FEE_ESTIMATES_USD"
    )

    # Verify key chains are covered
    assert '"base"' in source or "'base'" in source, "base chain must be in fee estimates"
    assert '"ethereum"' in source or "'ethereum'" in source, "ethereum chain must be in fee estimates"

    # Verify the default fee fallback exists
    assert "_DEFAULT_GAS_FEE_USD" in source, (
        "manager.py must define _DEFAULT_GAS_FEE_USD fallback"
    )
