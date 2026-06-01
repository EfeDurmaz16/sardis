#!/usr/bin/env python3
"""Generate TAP structural-verification vectors from the Python tap module.

GITIGNORED tooling. Drives `validate_tap_headers` over a fixed matrix (valid +
bad tag/alg/expired-window/created-not-past) and dumps the headers + expected
result so `@sardis/reference` `verifyTapRequest` is asserted identical.

Usage:
    python3 scripts/gen_tap_vectors.py > __tests__/vectors/tap.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SARDIS_SRC = Path(__file__).resolve().parents[2] / "sardis" / "src"
sys.path.insert(0, str(_SARDIS_SRC))

from sardis.protocol.tap import validate_tap_headers  # noqa: E402

NOW = 1_000_000
AUTHORITY = "merchant.example"
PATH = "/checkout"
SIG = "abcDEF123+/=="


def sig_input(created=NOW - 60, expires=NOW + 60, tag="agent-payer-auth", alg="ed25519", label="sig1"):
    return (
        f'{label}=("@authority" "@path");created={created};keyid="k1";'
        f'alg="{alg}";expires={expires};nonce="n-{created}-{expires}";tag="{tag}"'
    )


def sig_header(label="sig1", sig=SIG):
    return f"{label}=:{sig}:"


def run(name, si_header, sig_hdr, **kw):
    # Provide a fresh nonce cache so replay check passes (structural focus).
    res = validate_tap_headers(
        signature_input_header=si_header,
        signature_header=sig_hdr,
        authority=AUTHORITY,
        path=PATH,
        now=NOW,
        nonce_cache=set(),
    )
    return {
        "name": name,
        "signatureInput": si_header,
        "signature": sig_hdr,
        "now": NOW,
        "expected": {"accepted": res.accepted, "reason": res.reason},
    }


def main() -> None:
    vectors = [
        run("valid", sig_input(), sig_header()),
        run("bad_tag", sig_input(tag="nope"), sig_header()),
        run("bad_alg", sig_input(alg="rsa256"), sig_header()),
        run("expired", sig_input(created=NOW - 120, expires=NOW - 10), sig_header()),
        run("created_not_in_past", sig_input(created=NOW + 10, expires=NOW + 120), sig_header()),
        run("window_too_large", sig_input(created=NOW - 60, expires=NOW + 10_000), sig_header()),
        run("label_mismatch", sig_input(label="sig1"), sig_header(label="sig2")),
    ]
    json.dump(vectors, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
