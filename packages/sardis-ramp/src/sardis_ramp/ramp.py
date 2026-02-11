"""Sardis Fiat Ramp - Bridge integration for fiat on/off ramp."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import logging
from decimal import Decimal
from typing import Literal, Optional

import httpx

from .ramp_types import (
    BankAccount,
    FundingMethod,
    FundingResult,
    MerchantAccount,
    PaymentResult,
    RampConfig,
    WithdrawalResult,
    ACHDetails,
    WireDetails,
)

logger = logging.getLogger(__name__)


class PolicyViolation(Exception):
    """Raised when a transaction violates wallet policy."""
    pass


class KYCRequired(Exception):
    """Raised when KYC verification is required before proceeding."""
    pass


class SardisFiatRamp:
    """
    Sardis Fiat Ramp - Bridge crypto wallets to traditional banking.

    Enables:
    - Fund wallets from bank accounts or cards
    - Withdraw to bank accounts
    - Pay merchants in USD while settling from crypto

    Example:
        ramp = SardisFiatRamp(
            sardis_api_key="sk_...",
            bridge_api_key="bridge_..."
        )

        # Fund wallet from bank
        result = await ramp.fund_wallet(
            wallet_id="wallet_123",
            amount_usd=100.00,
            method="bank"
        )
        print(f"ACH routing: {result.ach_instructions.routing_number}")

        # Withdraw to bank
        withdrawal = await ramp.withdraw_to_bank(
            wallet_id="wallet_123",
            amount_usd=50.00,
            bank_account=BankAccount(
                account_holder_name="John Doe",
                account_number="1234567890",
                routing_number="021000021"
            )
        )
    """

    BRIDGE_API_URL = "https://api.bridge.xyz/v0"
    BRIDGE_SANDBOX_URL = "https://api.sandbox.bridge.xyz/v0"
    SARDIS_API_URL = "https://api.sardis.sh/v2"

    # KYC threshold for on-ramp (USD)
    KYC_THRESHOLD_USD = 1000.00

    def __init__(
        self,
        sardis_api_key: Optional[str] = None,
        bridge_api_key: Optional[str] = None,
        environment: Literal["sandbox", "production"] = "sandbox",
        config: Optional[RampConfig] = None,
        kyc_threshold_usd: float = 1000.00,
    ):
        """
        Initialize the fiat ramp.

        Args:
            sardis_api_key: Sardis API key (or set SARDIS_API_KEY env var)
            bridge_api_key: Bridge API key (or set BRIDGE_API_KEY env var)
            environment: "sandbox" or "production"
            config: Optional RampConfig object
            kyc_threshold_usd: KYC verification threshold in USD (default: $1000)
        """
        if config:
            self.sardis_api_key = config.sardis_api_key
            self.bridge_api_key = config.bridge_api_key
            self.environment = config.environment
        else:
            self.sardis_api_key = sardis_api_key or os.environ.get("SARDIS_API_KEY")
            self.bridge_api_key = bridge_api_key or os.environ.get("BRIDGE_API_KEY")
            self.environment = environment

        if not self.sardis_api_key:
            raise ValueError("Sardis API key required")
        if not self.bridge_api_key:
            raise ValueError("Bridge API key required")

        self.bridge_url = (
            self.BRIDGE_SANDBOX_URL if environment == "sandbox"
            else self.BRIDGE_API_URL
        )
        self.kyc_threshold_usd = kyc_threshold_usd
        self._webhook_secret = os.environ.get("BRIDGE_WEBHOOK_SECRET")
        self._max_retries = 3
        self._retry_delay = 1.0

        self._http = httpx.AsyncClient(timeout=30.0)

    async def _sardis_request(self, method: str, path: str, **kwargs) -> dict:
        """Make authenticated request to Sardis API."""
        resp = await self._http.request(
            method,
            f"{self.SARDIS_API_URL}{path}",
            headers={
                "Authorization": f"Bearer {self.sardis_api_key}",
                "Content-Type": "application/json",
            },
            **kwargs
        )
        resp.raise_for_status()
        return resp.json()

    async def _bridge_request(self, method: str, path: str, **kwargs) -> dict:
        """Make authenticated request to Bridge API with retry."""
        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.request(
                    method,
                    f"{self.bridge_url}{path}",
                    headers={
                        "Api-Key": self.bridge_api_key,
                        "Content-Type": "application/json",
                    },
                    **kwargs
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                # Retry on 429 and 5xx
                if e.response.status_code in (429, 500, 502, 503, 504):
                    if attempt < self._max_retries:
                        delay = self._retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Bridge API {method} {path} returned {e.response.status_code}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self._max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < self._max_retries:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Bridge API {method} {path} failed: {e}, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self._max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
        raise last_error

    async def get_wallet(self, wallet_id: str) -> dict:
        """Get wallet details from Sardis."""
        return await self._sardis_request("GET", f"/wallets/{wallet_id}")

    async def _check_kyc_status(self, wallet_id: str) -> dict:
        """
        Check KYC verification status for a wallet.

        Args:
            wallet_id: The Sardis wallet ID

        Returns:
            dict with 'verified' (bool), 'status' (str), 'inquiry_url' (str)
        """
        try:
            # Get wallet to find agent_id
            wallet = await self.get_wallet(wallet_id)
            agent_id = wallet.get("agent_id")

            if not agent_id:
                # No agent associated - cannot verify KYC
                return {
                    "verified": False,
                    "status": "no_agent",
                    "inquiry_url": "",
                }

            # Check KYC status via Sardis compliance endpoint
            kyc_result = await self._sardis_request(
                "GET",
                f"/agents/{agent_id}/kyc"
            )

            return {
                "verified": kyc_result.get("status") == "approved",
                "status": kyc_result.get("status", "not_started"),
                "inquiry_url": kyc_result.get("inquiry_url", ""),
                "inquiry_id": kyc_result.get("inquiry_id", ""),
            }
        except Exception as e:
            logger.warning(f"KYC check failed for wallet {wallet_id}: {e}")
            # Fail open in sandbox, fail closed in production
            if self.environment == "sandbox":
                return {
                    "verified": True,
                    "status": "sandbox_bypass",
                    "inquiry_url": "",
                }
            return {
                "verified": False,
                "status": "check_failed",
                "inquiry_url": "",
            }

    async def fund_wallet(
        self,
        wallet_id: str,
        amount_usd: float,
        method: FundingMethod | Literal["bank", "card", "crypto"] = "bank",
    ) -> FundingResult:
        """
        Fund a Sardis wallet from fiat sources.

        Args:
            wallet_id: The Sardis wallet ID to fund
            amount_usd: Amount in USD to deposit
            method: "bank" (ACH), "card" (credit/debit), or "crypto" (direct USDC)

        Returns:
            FundingResult with payment instructions or deposit address

        Raises:
            KYCRequired: If amount exceeds threshold and KYC is not verified
        """
        # KYC check for high-value on-ramp
        if amount_usd >= self.kyc_threshold_usd:
            kyc_status = await self._check_kyc_status(wallet_id)
            if not kyc_status.get("verified", False):
                raise KYCRequired(
                    f"KYC verification required for on-ramp amounts >= ${self.kyc_threshold_usd}. "
                    f"Please complete KYC verification before proceeding. "
                    f"Inquiry URL: {kyc_status.get('inquiry_url', '')}"
                )

        wallet = await self.get_wallet(wallet_id)

        if method == FundingMethod.CRYPTO or method == "crypto":
            # Direct crypto deposit - just return wallet address
            return FundingResult(
                type="crypto",
                deposit_address=wallet["address"],
                chain=wallet["chain"],
                token="USDC",
            )

        # Create Bridge transfer for fiat → USDC
        transfer = await self._bridge_request(
            "POST",
            "/transfers",
            json={
                "amount": str(amount_usd),
                "on_behalf_of": wallet_id,
                "source": {
                    "payment_rail": "ach" if method == "bank" else "card",
                    "currency": "usd",
                },
                "destination": {
                    "payment_rail": "ethereum",
                    "currency": "usdc",
                    "to_address": wallet["address"],
                    "chain": self._chain_to_bridge(wallet["chain"]),
                },
            }
        )

        # Parse ACH/Wire details if available
        ach_instructions = None
        wire_instructions = None

        if "source_deposit_instructions" in transfer:
            instr = transfer["source_deposit_instructions"]
            if instr.get("payment_rail") == "ach":
                ach_instructions = ACHDetails(
                    account_number=instr["account_number"],
                    routing_number=instr["routing_number"],
                    bank_name=instr["bank_name"],
                    account_holder=instr["account_holder"],
                    reference=instr["reference"],
                )
            elif instr.get("payment_rail") == "wire":
                wire_instructions = WireDetails(
                    account_number=instr["account_number"],
                    routing_number=instr["routing_number"],
                    swift_code=instr.get("swift_code", ""),
                    bank_name=instr["bank_name"],
                    bank_address=instr.get("bank_address", ""),
                    account_holder=instr["account_holder"],
                    reference=instr["reference"],
                )

        return FundingResult(
            type="fiat",
            payment_link=transfer.get("hosted_url"),
            ach_instructions=ach_instructions,
            wire_instructions=wire_instructions,
            estimated_arrival=transfer.get("estimated_completion_at"),
            fee_percent=Decimal(transfer.get("fee", {}).get("percent", "0")),
            transfer_id=transfer["id"],
        )

    async def withdraw_to_bank(
        self,
        wallet_id: str,
        amount_usd: float,
        bank_account: BankAccount,
    ) -> WithdrawalResult:
        """
        Withdraw from Sardis wallet to bank account.

        Args:
            wallet_id: The Sardis wallet ID to withdraw from
            amount_usd: Amount in USD to withdraw
            bank_account: Bank account details for payout

        Returns:
            WithdrawalResult with transaction details

        Raises:
            PolicyViolation: If withdrawal violates wallet policy
        """
        wallet = await self.get_wallet(wallet_id)

        # 1. Policy check
        policy_check = await self._sardis_request(
            "POST",
            f"/wallets/{wallet_id}/check-policy",
            json={
                "amount": str(amount_usd),
                "action": "withdrawal",
            }
        )

        if not policy_check.get("allowed", False):
            raise PolicyViolation(policy_check.get("reason", "Policy violation"))

        # 2. Get Bridge deposit address for USDC
        bridge_deposit = await self._bridge_request(
            "POST",
            "/deposit-addresses",
            json={
                "chain": self._chain_to_bridge(wallet["chain"]),
                "currency": "usdc",
            }
        )

        # 3. Send USDC to Bridge via Sardis
        tx = await self._sardis_request(
            "POST",
            "/transactions",
            json={
                "wallet_id": wallet_id,
                "to": bridge_deposit["address"],
                "amount": str(amount_usd),
                "token": "USDC",
                "memo": "Withdrawal to bank",
            }
        )

        # 4. Create Bridge payout to bank
        payout = await self._bridge_request(
            "POST",
            "/payouts",
            json={
                "amount": str(amount_usd),
                "currency": "usd",
                "source": {
                    "tx_hash": tx["tx_hash"],
                    "chain": self._chain_to_bridge(wallet["chain"]),
                },
                "destination": {
                    "payment_rail": "ach",
                    "account_holder_name": bank_account.account_holder_name,
                    "account_number": bank_account.account_number,
                    "routing_number": bank_account.routing_number,
                    "account_type": bank_account.account_type,
                },
            }
        )

        return WithdrawalResult(
            tx_hash=tx["tx_hash"],
            payout_id=payout["id"],
            estimated_arrival=payout["estimated_completion_at"],
            fee=Decimal(payout.get("fee", {}).get("amount", "0")),
            status="pending",
        )

    async def pay_merchant_fiat(
        self,
        wallet_id: str,
        amount_usd: float,
        merchant: MerchantAccount,
    ) -> PaymentResult:
        """
        Pay merchant in USD from crypto wallet.

        The agent pays in USDC, merchant receives USD in their bank.

        Args:
            wallet_id: The Sardis wallet ID to pay from
            amount_usd: Amount in USD to pay
            merchant: Merchant account to receive payment

        Returns:
            PaymentResult with transaction details

        Raises:
            PolicyViolation: If payment violates wallet policy
        """
        wallet = await self.get_wallet(wallet_id)

        # Policy check
        policy_check = await self._sardis_request(
            "POST",
            f"/wallets/{wallet_id}/check-policy",
            json={
                "amount": str(amount_usd),
                "merchant": merchant.name,
                "category": merchant.category,
            }
        )

        if not policy_check.get("allowed", False):
            raise PolicyViolation(policy_check.get("reason", "Policy violation"))

        if policy_check.get("requires_approval", False):
            # Request human approval
            approval = await self._sardis_request(
                "POST",
                f"/wallets/{wallet_id}/request-approval",
                json={
                    "amount": str(amount_usd),
                    "reason": f"Payment to {merchant.name}",
                }
            )
            return PaymentResult(
                status="pending_approval",
                approval_request=approval,
            )

        # Create payment via Bridge
        payment = await self._bridge_request(
            "POST",
            "/payments",
            json={
                "amount": str(amount_usd),
                "source": {
                    "wallet_address": wallet["address"],
                    "chain": self._chain_to_bridge(wallet["chain"]),
                    "currency": "usdc",
                },
                "destination": {
                    "payment_rail": "ach",
                    "currency": "usd",
                    "account_holder_name": merchant.bank_account.account_holder_name,
                    "account_number": merchant.bank_account.account_number,
                    "routing_number": merchant.bank_account.routing_number,
                },
            }
        )

        return PaymentResult(
            status="completed",
            payment_id=payment["id"],
            merchant_received=Decimal(amount_usd),
            fee=Decimal(payment.get("fee", {}).get("amount", "0")),
            tx_hash=payment.get("source_tx_hash"),
        )

    async def get_funding_status(self, transfer_id: str) -> dict:
        """Get status of a funding transfer."""
        return await self._bridge_request("GET", f"/transfers/{transfer_id}")

    async def get_withdrawal_status(self, payout_id: str) -> dict:
        """Get status of a bank withdrawal."""
        return await self._bridge_request("GET", f"/payouts/{payout_id}")

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Verify Bridge.xyz webhook HMAC-SHA256 signature.

        Args:
            payload: Raw request body bytes
            signature: Signature from Bridge-Signature header

        Returns:
            True if signature is valid
        """
        if not self._webhook_secret:
            logger.warning("Bridge webhook secret not configured")
            return False

        try:
            expected = hmac.new(
                self._webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            logger.error(f"Bridge webhook verification failed: {e}")
            return False

    def _chain_to_bridge(self, chain: str) -> str:
        """Convert Sardis chain name to Bridge chain name."""
        mapping = {
            "base": "base",
            "polygon": "polygon",
            "ethereum": "ethereum",
            "arbitrum": "arbitrum",
            "optimism": "optimism",
        }
        return mapping.get(chain.lower(), chain)

    async def close(self):
        """Close the HTTP client."""
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
