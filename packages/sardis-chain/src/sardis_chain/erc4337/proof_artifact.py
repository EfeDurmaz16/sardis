"""Proof artifact writer for ERC-4337 execution receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ERC4337ProofArtifact:
    path: str
    sha256: str


def write_erc4337_proof_artifact(
    *,
    base_dir: str,
    mandate_id: str,
    chain: str,
    wallet_id: str,
    smart_account: str,
    entrypoint: str,
    user_operation: dict[str, Any],
    user_op_hash: str,
    tx_hash: str,
    receipt: dict[str, Any],
) -> ERC4337ProofArtifact:
    now = datetime.now(timezone.utc)
    output_dir = Path(base_dir).expanduser() / chain / now.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    sanitized_hash = user_op_hash.replace("0x", "")[:12] or "unknown"
    file_name = f"{mandate_id}-{sanitized_hash}-{int(now.timestamp())}.json"
    file_path = output_dir / file_name

    payload = {
        "version": 1,
        "created_at": now.isoformat(),
        "mandate_id": mandate_id,
        "chain": chain,
        "wallet_id": wallet_id,
        "smart_account": smart_account,
        "entrypoint": entrypoint,
        "user_op_hash": user_op_hash,
        "tx_hash": tx_hash,
        "user_operation": user_operation,
        "receipt": receipt,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    payload["sha256"] = digest
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return ERC4337ProofArtifact(path=str(file_path), sha256=digest)

