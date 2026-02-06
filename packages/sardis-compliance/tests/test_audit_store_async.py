"""Tests for ComplianceEngine audit store async/sync wiring."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_compliance.checks import ComplianceAuditEntry, ComplianceEngine, ComplianceResult
from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate, VCProof


def _sample_payment_mandate(subject: str = "agent_123") -> PaymentMandate:
    return PaymentMandate(
        mandate_id="mnd_test",
        mandate_type="payment",
        issuer="did:web:sardis.network",
        subject=subject,
        expires_at=9999999999,
        nonce="nonce",
        proof=VCProof(
            verification_method="did:web:sardis.network#key-1",
            created="2026-01-01T00:00:00Z",
            proof_value="cHJvb2Y=",  # base64-ish placeholder
        ),
        domain="sardis.network",
        purpose="checkout",
        chain="base_sepolia",
        token="USDC",
        amount_minor=123,
        destination="0x0000000000000000000000000000000000000000",
        audit_hash="hash",
        wallet_id="wallet_123",
    )


class _AllowAllProvider:
    def evaluate(self, mandate: PaymentMandate) -> ComplianceResult:  # noqa: ARG002
        return ComplianceResult(allowed=True, provider="test", rule_id="allow_all")


class _AsyncStore:
    def __init__(self):
        self.calls = 0
        self.last_entry: ComplianceAuditEntry | None = None

    async def append(self, entry: ComplianceAuditEntry) -> str:
        self.calls += 1
        self.last_entry = entry
        return entry.audit_id


class _SyncStore:
    def __init__(self, audit_id: str = "audit_sync_1"):
        self.calls = 0
        self.audit_id = audit_id

    def append(self, entry: ComplianceAuditEntry) -> str:  # noqa: ARG002
        self.calls += 1
        return self.audit_id


@pytest.mark.asyncio
async def test_preflight_awaits_async_audit_store_append():
    store = _AsyncStore()
    engine = ComplianceEngine(SardisSettings(), provider=_AllowAllProvider(), audit_store=store)

    result = await engine.preflight(_sample_payment_mandate())

    assert store.calls == 1
    assert store.last_entry is not None
    assert result.audit_id == store.last_entry.audit_id


@pytest.mark.asyncio
async def test_preflight_supports_sync_audit_store_append():
    store = _SyncStore(audit_id="audit_sync_42")
    engine = ComplianceEngine(SardisSettings(), provider=_AllowAllProvider(), audit_store=store)

    result = await engine.preflight(_sample_payment_mandate())

    assert store.calls == 1
    assert result.audit_id == "audit_sync_42"

