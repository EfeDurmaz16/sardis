#!/usr/bin/env python3
"""Verify the TS-minted identity vector with the Python authority primitives.

The companion to `gen_identity_vectors.mjs`. Confirms that a Proof-of-Authority
MINTED in TS (`@sardis/reference` identity, dev seed) is accepted by the Python
`AuthorityProof.verify` with only the published public key — the cross-impl
issue↔verify moat. Run after regenerating the vector.

Usage:  python3 scripts/verify_identity_vectors.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SARDIS_SRC = Path(__file__).resolve().parents[2] / "sardis" / "src"
sys.path.insert(0, str(_SARDIS_SRC))

from sardis.core.authority_proof import AuthorityProof, public_key_b64url  # noqa: E402

_VEC = Path(__file__).resolve().parent.parent / "__tests__" / "vectors" / "identity-issue.json"


def main() -> int:
    vec = json.loads(_VEC.read_text())
    proof = AuthorityProof.from_jws(vec["jws"])
    pub = vec["publicKeyB64u"]
    ok = proof.verify(pub)
    same_key = public_key_b64url() == pub
    print(f"TS-minted JWS verifies in Python: {ok}")
    print(f"Python dev pubkey == vector key:  {same_key}")
    if not (ok and same_key):
        print("CROSS-IMPL MISMATCH", file=sys.stderr)
        return 1
    print("CROSS-IMPL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
