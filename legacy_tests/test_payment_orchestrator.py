from decimal import Decimal
from datetime import datetime, timezone

import pytest

from sardis_v2_core.mandates import CartMandate, IntentMandate, MandateChain, PaymentMandate, VCProof
from sardis_v2_core.orchestrator import PaymentOrchestrator
from sardis_wallet.manager import PolicyEvaluation
from sardis_compliance.checks import ComplianceResult
from sardis_chain.executor import ChainReceipt
from sardis_v2_core.transactions import Transaction


class StubWallet:
    def validate_policies(self, mandate: PaymentMandate) -> PolicyEvaluation:
        return PolicyEvaluation(allowed=True)


class StubCompliance:
    def preflight(self, mandate: PaymentMandate) -> ComplianceResult:
        return ComplianceResult(allowed=True)


class StubChain:
    async def dispatch_payment(self, mandate: PaymentMandate) -> ChainReceipt:
        return ChainReceipt(tx_hash="0xabc", chain=mandate.chain, block_number=1, audit_anchor="audit")


class StubLedger:
    def append(self, payment_mandate: PaymentMandate, chain_receipt: ChainReceipt) -> Transaction:
        return Transaction(
            from_wallet=payment_mandate.subject,
            to_wallet=payment_mandate.destination,
            amount=Decimal(payment_mandate.amount_minor) / Decimal(100),
            currency=payment_mandate.token,
            audit_anchor=chain_receipt.audit_anchor,
        )


def _vc_proof() -> VCProof:
    return VCProof(
        type="DataIntegrityProof",
        verification_method="did:agent#ed25519:stub",
        created=datetime.now(timezone.utc).isoformat(),
        proof_value="c2lnbg==",
    )


def _mandate_chain() -> MandateChain:
    intent = IntentMandate(
        mandate_id="intent-1",
        mandate_type="intent",
        issuer="sardis",
        subject="agent",
        expires_at=9999999999,
        nonce="intent",
        proof=_vc_proof(),
        domain="merchant.example",
        purpose="intent",
        scope=["digital"],
        requested_amount=100_00,
    )
    cart = CartMandate(
        mandate_id="cart-1",
        mandate_type="cart",
        issuer="sardis",
        subject="agent",
        expires_at=9999999999,
        nonce="cart",
        proof=_vc_proof(),
        domain="merchant.example",
        purpose="cart",
        line_items=[{"sku": "sku-1", "description": "Item", "amount_minor": 100_00}],
        merchant_domain="merchant.example",
        currency="USD",
        subtotal_minor=100_00,
        taxes_minor=0,
    )
    payment = PaymentMandate(
        mandate_id="payment-1",
        mandate_type="payment",
        issuer="sardis",
        subject="agent",
        expires_at=9999999999,
        nonce="pay",
        proof=_vc_proof(),
        domain="merchant.example",
        purpose="checkout",
        chain="base",
        token="USDC",
        amount_minor=100_00,
        destination="0xmerchant",
        audit_hash="audit",
    )
    return MandateChain(intent=intent, cart=cart, payment=payment)


@pytest.mark.asyncio
async def test_payment_orchestrator_happy_path():
    orchestrator = PaymentOrchestrator(
        wallet_manager=StubWallet(),
        compliance=StubCompliance(),
        chain_executor=StubChain(),
        ledger=StubLedger(),
    )
    result = await orchestrator.execute_chain(_mandate_chain())
    assert result.mandate_id == "payment-1"
    assert result.chain_tx_hash == "0xabc"
    assert result.status == "submitted"
