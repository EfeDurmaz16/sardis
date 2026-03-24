"""
Fuzz test for the spending policy engine.

Uses Google's Atheris fuzzer to generate random inputs and verify that
the spending policy engine never crashes — it should always return a
clean (bool, str) result or raise a well-defined exception.

Run manually:
    python tests/fuzz/fuzz_spending_policy.py

In CI, duration is controlled by FUZZING_DURATION env var (seconds).
"""
from __future__ import annotations

import os
import struct
import sys

import atheris


def fuzz_validate_payment(data: bytes) -> None:
    """Fuzz SpendingPolicy.validate_payment with random amounts and scopes."""
    from decimal import Decimal, InvalidOperation

    from sardis_v2_core.spending_policy import SpendingPolicy, SpendingScope, TrustLevel

    fdp = atheris.FuzzedDataProvider(data)

    # Build random policy parameters
    trust_choices = list(TrustLevel)
    scope_choices = list(SpendingScope)

    trust_idx = fdp.ConsumeIntInRange(0, len(trust_choices) - 1)
    scope_idx = fdp.ConsumeIntInRange(0, len(scope_choices) - 1)
    per_tx = fdp.ConsumeFloatInRange(0.0, 1e12)
    total = fdp.ConsumeFloatInRange(0.0, 1e12)

    try:
        policy = SpendingPolicy(
            trust_level=trust_choices[trust_idx],
            allowed_scopes=[scope_choices[scope_idx]],
            per_transaction_limit=Decimal(str(per_tx)),
            total_limit=Decimal(str(total)),
        )
    except (InvalidOperation, ValueError, OverflowError):
        return

    # Fuzz the payment amount
    amount_bytes = fdp.ConsumeBytes(8)
    if len(amount_bytes) < 8:
        amount_bytes = amount_bytes.ljust(8, b"\x00")
    raw_amount = struct.unpack("d", amount_bytes)[0]

    try:
        amount = Decimal(str(raw_amount))
    except (InvalidOperation, ValueError, OverflowError):
        return

    fee_bytes = fdp.ConsumeBytes(8)
    if len(fee_bytes) < 8:
        fee_bytes = fee_bytes.ljust(8, b"\x00")
    raw_fee = struct.unpack("d", fee_bytes)[0]

    try:
        fee = Decimal(str(raw_fee))
    except (InvalidOperation, ValueError, OverflowError):
        return

    scope_str = fdp.ConsumeUnicodeNoSurrogates(50)
    merchant = fdp.ConsumeUnicodeNoSurrogates(100)
    mcc = fdp.ConsumeUnicodeNoSurrogates(10)

    # This must never crash — always return (bool, str) or raise cleanly
    try:
        result = policy.validate_payment(
            amount=amount,
            fee=fee,
            scope=scope_str,
            merchant_name=merchant,
            mcc_code=mcc,
        )
        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
        assert len(result) == 2, f"Expected 2-tuple, got {len(result)}-tuple"
        assert isinstance(result[0], bool), f"Expected bool, got {type(result[0])}"
        assert isinstance(result[1], str), f"Expected str, got {type(result[1])}"
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        # These are acceptable — the policy rejects bad input gracefully
        pass


def main() -> None:
    duration = int(os.environ.get("FUZZING_DURATION", "30"))
    atheris.Setup(
        sys.argv + [f"-max_total_time={duration}", "-len_control=100"],
        fuzz_validate_payment,
    )
    atheris.Fuzz()


if __name__ == "__main__":
    main()
