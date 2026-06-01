#!/usr/bin/env python3
"""Generate x402 / ERC-3009 vectors from the Python verifier + eth_account.

GITIGNORED tooling. Produces:
  - the EIP-712 signing DIGEST (so the TS keccak digest is asserted byte-equal),
  - a real signed authorization from a fixed test EOA (test-only key),
  - the recovered signer + expected verify outcomes,
  - timing failure vectors with exact reason codes from validate_authorization_timing.

Usage:
    python3 scripts/gen_x402_vectors.py > __tests__/vectors/x402.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SARDIS_SRC = Path(__file__).resolve().parents[2] / "sardis" / "src"
sys.path.insert(0, str(_SARDIS_SRC))

from eth_account import Account  # noqa: E402
from eth_account.messages import encode_typed_data  # noqa: E402
from eth_utils import keccak  # noqa: E402

from sardis.protocol.x402_erc3009 import (  # noqa: E402
    TRANSFER_WITH_AUTHORIZATION_TYPE,
    ERC3009Authorization,
    resolve_eip712_domain,
    validate_authorization_timing,
    verify_transfer_authorization,
)

# Fixed test-only private key (NOT a real key — deterministic for vectors).
TEST_PRIVKEY = "0x" + "11" * 32
acct = Account.from_key(TEST_PRIVKEY)

NETWORK = "base"
NOW = 1_000_000
NONCE = "0x" + "ab" * 32


def make_auth(value=5_000_000, valid_after=NOW - 100, valid_before=NOW + 100) -> ERC3009Authorization:
    return ERC3009Authorization(
        from_address=acct.address,
        to_address="0x" + "cd" * 20,
        value=value,
        valid_after=valid_after,
        valid_before=valid_before,
        nonce=NONCE,
    )


def sign(auth: ERC3009Authorization) -> str:
    domain = resolve_eip712_domain(NETWORK)
    message = {
        "from": auth.from_address,
        "to": auth.to_address,
        "value": int(auth.value),
        "validAfter": int(auth.valid_after),
        "validBefore": int(auth.valid_before),
        "nonce": bytes.fromhex(auth.nonce[2:]),
    }
    signable = encode_typed_data(domain, {"TransferWithAuthorization": TRANSFER_WITH_AUTHORIZATION_TYPE}, message)
    signed = acct.sign_message(signable)
    # SignableMessage = (version=0x01, header=domainSeparator, body=hashStruct).
    # The EIP-712 signing digest is keccak(0x19 || version || header || body)
    # = keccak(0x19 0x01 || domainSeparator || hashStruct).
    digest = keccak(b"\x19" + signable.version + signable.header + signable.body)
    return "0x" + signed.signature.hex(), "0x" + digest.hex()


def auth_json(auth: ERC3009Authorization) -> dict:
    return {
        "fromAddress": auth.from_address,
        "toAddress": auth.to_address,
        "value": str(auth.value),
        "validAfter": auth.valid_after,
        "validBefore": auth.valid_before,
        "nonce": auth.nonce,
    }


def main() -> None:
    valid = make_auth()
    signature, digest = sign(valid)
    ok, reason = verify_transfer_authorization(valid, signature, network=NETWORK, expected_payer=acct.address, now=NOW)

    # Timing failures (validate_authorization_timing is pure).
    expired = make_auth(valid_after=NOW - 200, valid_before=NOW - 100)
    not_yet = make_auth(valid_after=NOW + 100, valid_before=NOW + 200)
    inverted = make_auth(valid_after=NOW + 100, valid_before=NOW - 100)

    def timing(a):
        ok2, r = validate_authorization_timing(a, now=NOW)
        return {"ok": ok2, "reason": r}

    out = {
        "network": NETWORK,
        "now": NOW,
        "signer": acct.address,
        "valid": {
            "auth": auth_json(valid),
            "signature": signature,
            "eip712Digest": digest,
            "recoveredSigner": acct.address,
            "expectedPayer": acct.address,
            "verify": {"ok": ok, "reason": reason},
        },
        "binding": {
            # signer != from (use a different from address) -> signer_mismatch_authorization_from
            "wrong_from": auth_json(make_auth())  # same; mismatch is asserted in TS by passing a different recovered signer
        },
        "timing": {
            "expired": {"auth": auth_json(expired), "expected": timing(expired)},
            "not_yet_valid": {"auth": auth_json(not_yet), "expected": timing(not_yet)},
            "inverted_window": {"auth": auth_json(inverted), "expected": timing(inverted)},
        },
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
