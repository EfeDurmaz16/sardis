"""x402 client — pays x402-protected APIs on behalf of agents.

Implements the purl patterns:
- Negotiator: select_best() scores payment options
- Dry-run: preview cost without executing
- Protocol abstraction: wraps x402 behind control plane interface
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    pass

from .x402_policy_guard import X402PolicyDenied, X402PolicyGuard

logger = logging.getLogger(__name__)


class MPCSigner(Protocol):
    """Interface for MPC signing."""
    async def sign_eip712(self, typed_data: dict, wallet_id: str) -> str: ...


class SettlementStore(Protocol):
    """Interface for settlement persistence."""
    async def save(self, settlement: Any) -> None: ...
    async def get(self, payment_id: str) -> Any | None: ...


@dataclass
class X402AcceptOption:
    """A single payment option from a 402 challenge accepts array."""
    network: str = "base"
    currency: str = "USDC"
    amount: str = "0"
    token_address: str = ""
    scheme: str = "exact"


@dataclass
class X402CostPreview:
    """Result of a dry-run cost preview."""
    amount: str = "0"
    currency: str = "USDC"
    network: str = "base"
    policy_would_allow: bool = False
    failure_reasons: list[str] = field(default_factory=list)
    estimated_gas: str = "0"
    scheme: str = "exact"


class X402Negotiator:
    """Selects best payment option from 402 challenge accepts array.

    Scoring criteria (purl pattern):
    1. Chain with highest available balance
    2. Lowest estimated gas cost
    3. Matching preferred token
    """

    def select_best(
        self,
        accepts: list[X402AcceptOption],
        available_balances: dict[str, Decimal] | None = None,
        preferred_chains: list[str] | None = None,
    ) -> X402AcceptOption | None:
        if not accepts:
            return None

        balances = available_balances or {}
        preferred = set(preferred_chains or [])

        def score(opt: X402AcceptOption) -> tuple[int, Decimal]:
            chain_pref = 2 if opt.network in preferred else 0
            balance = balances.get(f"{opt.network}:{opt.currency}", Decimal("0"))
            return (chain_pref, balance)

        ranked = sorted(accepts, key=score, reverse=True)
        return ranked[0]


class X402Client:
    """HTTP client that handles 402 payment flows for agents.

    Usage:
        client = X402Client(control_plane=cp, policy_guard=guard, ...)
        response = await client.request("GET", "https://api.example.com/data",
                                         agent_id="agent_1", org_id="org_1", wallet_id="wal_1")
    """

    def __init__(
        self,
        policy_guard: X402PolicyGuard,
        mpc_signer: MPCSigner | None = None,
        settlement_store: SettlementStore | None = None,
        negotiator: X402Negotiator | None = None,
        max_cost: str = "100",
        preferred_networks: list[str] | None = None,
    ) -> None:
        self._policy_guard = policy_guard
        self._mpc_signer = mpc_signer
        self._settlement_store = settlement_store
        self._negotiator = negotiator or X402Negotiator()
        self._max_cost = Decimal(max_cost)
        self._preferred_networks = preferred_networks or ["base"]

    async def request(
        self,
        method: str,
        url: str,
        agent_id: str,
        org_id: str,
        wallet_id: str,
        *,
        max_cost: str | None = None,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an HTTP request, handling 402 payment automatically.

        Returns a dict with keys: status_code, headers, body, payment (if paid).
        """
        import httpx

        effective_max = Decimal(max_cost) if max_cost else self._max_cost

        async with httpx.AsyncClient() as http:
            response = await http.request(method, url, **kwargs)

            if response.status_code != 402:
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text,
                    "payment": None,
                }

            return await self._handle_402(
                http, response, method, url,
                agent_id, org_id, wallet_id,
                effective_max, dry_run,
                **kwargs,
            )

    async def _handle_402(
        self,
        http: Any,
        response: Any,
        method: str,
        url: str,
        agent_id: str,
        org_id: str,
        wallet_id: str,
        max_cost: Decimal,
        dry_run: bool,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Handle a 402 response by negotiating and paying."""
        from sardis_protocol.x402 import (
            X402Challenge,
            X402HeaderBuilder,
            X402PaymentPayload,
            parse_challenge_header,
        )

        # Parse challenge from response header
        challenge_header = response.headers.get("PaymentRequired", "")
        if not challenge_header:
            return {
                "status_code": 402,
                "headers": dict(response.headers),
                "body": response.text,
                "payment": None,
                "error": "no_challenge_header",
            }

        challenge: X402Challenge = parse_challenge_header(challenge_header)

        # Safety cap check
        amount_decimal = Decimal(challenge.amount) / Decimal("1000000")
        if amount_decimal > max_cost:
            raise X402PolicyDenied(
                f"Amount ${amount_decimal} exceeds max cost ${max_cost}",
                remaining=str(max_cost),
            )

        # Run through control plane policy check
        ok, reason = await self._policy_guard.evaluate(
            challenge, agent_id, org_id, wallet_id,
        )
        if not ok:
            raise X402PolicyDenied(reason)

        if dry_run:
            return {
                "status_code": 402,
                "headers": dict(response.headers),
                "body": response.text,
                "payment": {
                    "payment_id": challenge.payment_id,
                    "amount": challenge.amount,
                    "currency": challenge.currency,
                    "network": challenge.network,
                    "dry_run": True,
                    "policy_would_allow": True,
                },
            }

        # Sign ERC-3009 authorization via MPC
        signature = ""
        if self._mpc_signer is not None:
            from sardis_protocol.x402_erc3009 import build_transfer_authorization
            typed_data = build_transfer_authorization(
                from_addr="0x" + "0" * 40,  # Filled by MPC signer
                to_addr=challenge.payee_address,
                value=int(challenge.amount),
                valid_after=0,
                valid_before=challenge.expires_at,
                nonce=challenge.nonce,
            )
            signature = await self._mpc_signer.sign_eip712(typed_data, wallet_id)

        # Build payment payload
        payload = X402PaymentPayload(
            payment_id=challenge.payment_id,
            payer_address="",  # Filled by wallet
            amount=challenge.amount,
            nonce=challenge.nonce,
            signature=signature,
        )

        # Retry with payment header
        payment_headers = X402HeaderBuilder.build_payment_signature_header(payload)
        existing_headers = kwargs.pop("headers", {})
        merged_headers = {**existing_headers, **payment_headers}

        retry_response = await http.request(method, url, headers=merged_headers, **kwargs)

        payment_info = {
            "payment_id": challenge.payment_id,
            "amount": challenge.amount,
            "currency": challenge.currency,
            "network": challenge.network,
            "tx_hash": "",
            "dry_run": False,
        }

        # Parse receipt from response
        receipt_header = retry_response.headers.get("PAYMENT-RESPONSE", "")
        if receipt_header:
            try:
                import base64
                import json
                receipt = json.loads(base64.b64decode(receipt_header))
                payment_info["tx_hash"] = receipt.get("tx_hash", "")
            except Exception:
                pass

        return {
            "status_code": retry_response.status_code,
            "headers": dict(retry_response.headers),
            "body": retry_response.text,
            "payment": payment_info,
        }

    async def dry_run(
        self,
        url: str,
        agent_id: str,
        org_id: str,
        wallet_id: str,
    ) -> X402CostPreview:
        """Preview cost without paying (purl's --dry-run)."""
        import httpx

        async with httpx.AsyncClient() as http:
            response = await http.get(url)
            if response.status_code != 402:
                return X402CostPreview(
                    policy_would_allow=True,
                    failure_reasons=["endpoint_does_not_require_payment"],
                )

            from sardis_protocol.x402 import parse_challenge_header

            challenge_header = response.headers.get("PaymentRequired", "")
            if not challenge_header:
                return X402CostPreview(failure_reasons=["no_challenge_header"])

            challenge = parse_challenge_header(challenge_header)

            ok, reason = await self._policy_guard.evaluate(
                challenge, agent_id, org_id, wallet_id,
            )

            return X402CostPreview(
                amount=challenge.amount,
                currency=challenge.currency,
                network=challenge.network,
                policy_would_allow=ok,
                failure_reasons=[reason] if reason else [],
            )


__all__ = [
    "X402Client",
    "X402Negotiator",
    "X402AcceptOption",
    "X402CostPreview",
]
