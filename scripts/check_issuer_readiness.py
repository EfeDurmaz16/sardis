#!/usr/bin/env python3
"""Print local card issuer readiness from environment variables."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "packages" / "sardis-cards" / "src"))

from sardis_cards.providers import evaluate_issuer_readiness  # noqa: E402


def main() -> int:
    rows = []
    for item in evaluate_issuer_readiness():
        rows.append(
            {
                "name": item.name,
                "configured": item.configured,
                "stablecoin_native": item.stablecoin_native,
                "card_issuing": item.card_issuing,
                "missing_env": list(item.missing_env),
                "notes": item.notes,
            }
        )
    print(json.dumps({"issuers": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
