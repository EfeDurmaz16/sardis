"""Stripe Stablecoin-Backed Card Issuing integration.

Enables USDC-funded Visa prepaid cards via Stripe Connect + Financial Accounts v2.
Agent USDC balance on Base is sent to a Stripe-provided deposit address,
and Stripe handles the USDC->USD conversion at card-spend time.

Flow:
1. Create a Connected Account (one per agent/org)
2. Create a Financial Account v2 with USDC support
3. Get the USDC deposit address on Base
4. Agent sends USDC to that address
5. Stripe converts USDC->USD at spend time
6. Card works at any Visa merchant worldwide

Requirements:
- Stripe API key with Issuing + Treasury + Connect access
- Stripe stablecoin-backed card issuing private preview enabled
- Base chain support (USDC on Base)

API Reference: https://docs.stripe.com/connect/stablecoin-backed-card-issuing
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────


SUPPORTED_STABLECOIN_CURRENCIES = ["usdc"]
SUPPORTED_CHAINS = ["base"]  # Stripe currently supports Base only
USDC_BASE_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


class StablecoinAccountStatus(str, Enum):
    """Financial account status."""
    OPEN = "open"
    CLOSED = "closed"
    RESTRICTED = "restricted"


class DepositStatus(str, Enum):
    """USDC deposit status."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class FundingTransferStatus(str, Enum):
    """Card funding transfer status."""
    PENDING = "pending"
    PROCESSING = "processing"
    POSTED = "posted"
    FAILED = "failed"


# ── Data Models ────────────────────────────────────────────────────────


@dataclass
class StablecoinFinancialAccount:
    """Stripe Financial Account v2 with USDC support."""
    account_id: str
    connected_account_id: str
    status: StablecoinAccountStatus = StablecoinAccountStatus.OPEN
    usdc_balance: Decimal = Decimal("0")
    usd_balance: Decimal = Decimal("0")
    deposit_address: str | None = None
    deposit_chain: str = "base"
    supported_currencies: list[str] = field(default_factory=lambda: ["usdc", "usd"])
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StablecoinDeposit:
    """Record of a USDC deposit to a Stripe financial account."""
    deposit_id: str
    financial_account_id: str
    amount: Decimal
    currency: str = "usdc"
    chain: str = "base"
    tx_hash: str | None = None
    status: DepositStatus = DepositStatus.PENDING
    confirmed_at: datetime | None = None
    created_at: datetime | None = None


@dataclass
class StablecoinCardFunding:
    """Transfer from stablecoin balance to card spending power."""
    transfer_id: str
    financial_account_id: str
    amount: Decimal
    from_currency: str = "usdc"
    status: FundingTransferStatus = FundingTransferStatus.PENDING
    card_id: str | None = None
    created_at: datetime | None = None


class StripeStablecoinError(Exception):
    """Error from Stripe Stablecoin APIs."""
    pass


# ── Client ─────────────────────────────────────────────────────────────


class StripeStablecoinClient:
    """Client for Stripe Stablecoin-Backed Card Issuing.

    Manages the full lifecycle:
    - Connected account creation for agents
    - Financial Account v2 with USDC support
    - USDC deposit address on Base
    - Balance monitoring
    - Card issuance backed by stablecoin balance

    Usage:
        client = StripeStablecoinClient(api_key="sk_...")
        account = await client.create_connected_account("Agent Corp")
        fa = await client.create_financial_account(account.connected_account_id)
        address = fa.deposit_address  # Send USDC here on Base
    """

    def __init__(self, api_key: str):
        try:
            import stripe
        except ImportError:
            raise ImportError(
                "Stripe SDK not installed. Install with: pip install stripe"
            )

        self._api_key = api_key
        self._stripe = stripe
        self._stripe.api_key = api_key
        self._is_test_mode = api_key.startswith("sk_test_")

    # ── Connected Accounts ────────────────────────────────────────

    async def create_connected_account(
        self,
        business_name: str,
        *,
        email: str | None = None,
        country: str = "US",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe Connect account for an agent/organization.

        Each agent org gets its own connected account which holds
        the stablecoin financial account and issued cards.

        Args:
            business_name: Display name for the connected account
            email: Contact email
            country: Country code (US only for private preview)
            metadata: Additional metadata (wallet_id, agent_id, etc.)

        Returns:
            Dict with account_id and details
        """
        try:
            account = await asyncio.to_thread(
                self._stripe.Account.create,
                type="custom",
                country=country,
                email=email,
                business_type="company",
                company={"name": business_name},
                capabilities={
                    "card_issuing": {"requested": True},
                    "treasury": {"requested": True},
                },
                metadata={
                    "managed_by": "sardis",
                    **(metadata or {}),
                },
            )
            logger.info(
                "Created connected account %s for %s",
                account.id, business_name,
            )
            return {
                "account_id": account.id,
                "business_name": business_name,
                "country": country,
                "capabilities_requested": ["card_issuing", "treasury"],
            }
        except Exception as e:
            raise StripeStablecoinError(
                f"Failed to create connected account: {e}"
            ) from e

    # ── Financial Accounts (v2) ───────────────────────────────────

    async def create_financial_account(
        self,
        connected_account_id: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> StablecoinFinancialAccount:
        """Create a Financial Account v2 with USDC support on Base.

        This is the core stablecoin account that holds USDC and
        backs issued cards. Stripe provides a deposit address on Base
        where USDC can be sent.

        Args:
            connected_account_id: Stripe Connect account ID (acct_...)
            metadata: Additional metadata

        Returns:
            StablecoinFinancialAccount with deposit address
        """
        try:
            # Create Financial Account with stablecoin support
            # Uses v2 API with supported_currencies including "usdc"
            fa = await asyncio.to_thread(
                self._stripe.treasury.FinancialAccount.create,
                supported_currencies=["usd", "usdc"],
                features={
                    "inbound_transfers": {"ach": {"requested": True}},
                    "outbound_payments": {"ach": {"requested": True}},
                    "card_issuing": {"requested": True},
                },
                metadata={
                    "managed_by": "sardis",
                    "stablecoin_enabled": "true",
                    **(metadata or {}),
                },
                stripe_account=connected_account_id,
            )

            # Get the crypto deposit address for USDC on Base
            deposit_address = await self._get_deposit_address(
                fa.id, connected_account_id
            )

            account = StablecoinFinancialAccount(
                account_id=fa.id,
                connected_account_id=connected_account_id,
                status=StablecoinAccountStatus.OPEN,
                deposit_address=deposit_address,
                deposit_chain="base",
                created_at=datetime.now(UTC),
                metadata=metadata or {},
            )

            logger.info(
                "Created stablecoin financial account %s (deposit: %s)",
                fa.id, deposit_address,
            )
            return account

        except StripeStablecoinError:
            raise
        except Exception as e:
            raise StripeStablecoinError(
                f"Failed to create financial account: {e}"
            ) from e

    async def _get_deposit_address(
        self,
        financial_account_id: str,
        connected_account_id: str,
    ) -> str | None:
        """Get the USDC deposit address on Base for a financial account.

        Stripe assigns a unique Base address per financial account.
        USDC sent to this address is credited to the account balance.
        """
        try:
            # Retrieve financial account details which include crypto addresses
            fa = await asyncio.to_thread(
                self._stripe.treasury.FinancialAccount.retrieve,
                financial_account_id,
                expand=["financial_addresses"],
                stripe_account=connected_account_id,
            )

            # Extract the crypto address for Base USDC
            addresses = getattr(fa, "financial_addresses", None)
            if addresses and hasattr(addresses, "data"):
                for addr in addresses.data:
                    if getattr(addr, "type", "") == "crypto" and \
                       getattr(addr, "network", "") == "base":
                        return getattr(addr, "address", None)

            # Fallback: check nested structure
            fa_dict = fa.to_dict() if hasattr(fa, "to_dict") else {}
            for addr in fa_dict.get("financial_addresses", {}).get("data", []):
                if addr.get("type") == "crypto" and addr.get("network") == "base":
                    return addr.get("address")

            return None
        except Exception as e:
            logger.warning("Could not get deposit address: %s", e)
            return None

    async def get_financial_account(
        self,
        financial_account_id: str,
        connected_account_id: str,
    ) -> StablecoinFinancialAccount:
        """Get financial account details including balances.

        Args:
            financial_account_id: Stripe Financial Account ID (fa_...)
            connected_account_id: Stripe Connect account ID (acct_...)

        Returns:
            StablecoinFinancialAccount with current balances
        """
        try:
            fa = await asyncio.to_thread(
                self._stripe.treasury.FinancialAccount.retrieve,
                financial_account_id,
                stripe_account=connected_account_id,
            )

            fa_dict = fa.to_dict() if hasattr(fa, "to_dict") else fa

            # Parse balances - v2 accounts have both USD and USDC
            balance = fa_dict.get("balance", {})
            cash = balance.get("cash", {})
            usdc_balance = Decimal(str(cash.get("usdc", 0))) / 100
            usd_balance = Decimal(str(cash.get("usd", 0))) / 100

            deposit_address = await self._get_deposit_address(
                financial_account_id, connected_account_id
            )

            return StablecoinFinancialAccount(
                account_id=financial_account_id,
                connected_account_id=connected_account_id,
                status=StablecoinAccountStatus(fa_dict.get("status", "open")),
                usdc_balance=usdc_balance,
                usd_balance=usd_balance,
                deposit_address=deposit_address,
            )
        except Exception as e:
            raise StripeStablecoinError(
                f"Failed to get financial account: {e}"
            ) from e

    # ── Balance ───────────────────────────────────────────────────

    async def get_stablecoin_balance(
        self,
        financial_account_id: str,
        connected_account_id: str,
    ) -> dict[str, Decimal]:
        """Get USDC and USD balances for a financial account.

        Returns:
            Dict with 'usdc' and 'usd' balances
        """
        account = await self.get_financial_account(
            financial_account_id, connected_account_id
        )
        return {
            "usdc": account.usdc_balance,
            "usd": account.usd_balance,
            "total_usd_equivalent": account.usdc_balance + account.usd_balance,
        }

    # ── Card Issuance ─────────────────────────────────────────────

    async def create_stablecoin_card(
        self,
        connected_account_id: str,
        cardholder_id: str,
        *,
        spending_limits: list[dict[str, Any]] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a Visa prepaid card backed by stablecoin balance.

        The card draws from the USDC financial account balance.
        Stripe converts USDC->USD at the point of sale.

        Args:
            connected_account_id: Stripe Connect account (acct_...)
            cardholder_id: Stripe Issuing cardholder (ich_...)
            spending_limits: Optional per-tx/daily/monthly limits
            metadata: Additional metadata

        Returns:
            Dict with card details
        """
        try:
            spending_controls = {}
            if spending_limits:
                spending_controls["spending_limits"] = spending_limits

            card = await asyncio.to_thread(
                self._stripe.issuing.Card.create,
                cardholder=cardholder_id,
                currency="usd",
                type="virtual",
                status="active",
                spending_controls=spending_controls or None,
                metadata={
                    "managed_by": "sardis",
                    "funding_source": "stablecoin",
                    **(metadata or {}),
                },
                stripe_account=connected_account_id,
            )

            logger.info(
                "Created stablecoin-backed card %s on account %s",
                card.id, connected_account_id,
            )
            return {
                "card_id": card.id,
                "last4": card.last4,
                "exp_month": card.exp_month,
                "exp_year": card.exp_year,
                "status": card.status,
                "type": "virtual",
                "funding_source": "stablecoin",
                "connected_account_id": connected_account_id,
            }
        except Exception as e:
            raise StripeStablecoinError(
                f"Failed to create stablecoin card: {e}"
            ) from e

    async def create_cardholder(
        self,
        connected_account_id: str,
        *,
        name: str,
        email: str,
        phone: str | None = None,
        billing_address: dict[str, str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Create a cardholder on a connected account.

        Args:
            connected_account_id: Stripe Connect account
            name: Cardholder full name
            email: Contact email
            phone: Phone number
            billing_address: Billing address dict
            metadata: Additional metadata

        Returns:
            Cardholder ID (ich_...)
        """
        address = billing_address or {
            "line1": "354 Oyster Point Blvd",
            "city": "South San Francisco",
            "state": "CA",
            "postal_code": "94080",
            "country": "US",
        }

        parts = name.strip().split(None, 1)
        first_name = parts[0] if parts else name
        last_name = parts[1] if len(parts) > 1 else ""

        try:
            cardholder = await asyncio.to_thread(
                self._stripe.issuing.Cardholder.create,
                type="individual",
                name=name,
                email=email,
                phone_number=phone or "+15555550100",
                individual={
                    "first_name": first_name,
                    "last_name": last_name or "Agent",
                },
                billing={"address": address},
                metadata={
                    "managed_by": "sardis",
                    **(metadata or {}),
                },
                stripe_account=connected_account_id,
            )
            return cardholder.id
        except Exception as e:
            raise StripeStablecoinError(
                f"Failed to create cardholder: {e}"
            ) from e

    # ── Deposit Monitoring ────────────────────────────────────────

    async def list_received_credits(
        self,
        financial_account_id: str,
        connected_account_id: str,
        *,
        limit: int = 20,
    ) -> list[StablecoinDeposit]:
        """List USDC deposits received by a financial account.

        Monitors incoming USDC transfers on Base.

        Args:
            financial_account_id: Financial Account ID
            connected_account_id: Connect account ID
            limit: Max results

        Returns:
            List of StablecoinDeposit records
        """
        try:
            credits = await asyncio.to_thread(
                self._stripe.treasury.ReceivedCredit.list,
                financial_account=financial_account_id,
                limit=limit,
                stripe_account=connected_account_id,
            )

            deposits = []
            for credit in credits.data:
                credit_dict = credit.to_dict() if hasattr(credit, "to_dict") else credit
                amount = Decimal(str(credit_dict.get("amount", 0))) / 100
                currency = credit_dict.get("currency", "usd")

                deposits.append(StablecoinDeposit(
                    deposit_id=credit_dict.get("id", ""),
                    financial_account_id=financial_account_id,
                    amount=amount,
                    currency=currency,
                    chain="base" if currency == "usdc" else "",
                    tx_hash=credit_dict.get("network_details", {}).get("tx_hash"),
                    status=DepositStatus.CONFIRMED if credit_dict.get("status") == "succeeded" else DepositStatus.PENDING,
                    created_at=datetime.fromtimestamp(
                        credit_dict.get("created", 0), tz=UTC
                    ) if credit_dict.get("created") else None,
                ))
            return deposits
        except Exception as e:
            raise StripeStablecoinError(
                f"Failed to list deposits: {e}"
            ) from e

    async def close(self) -> None:
        """No-op for Stripe SDK (uses module-level config)."""
        pass


# ── High-Level Service ─────────────────────────────────────────────────


class StablecoinCardService:
    """High-level service for stablecoin-backed card operations.

    Provides simplified interface for the full lifecycle:
    1. Onboard agent → create connected account + financial account
    2. Fund → get deposit address, agent sends USDC
    3. Issue card → create cardholder + virtual card
    4. Monitor → check balances and deposits
    """

    def __init__(self, client: StripeStablecoinClient):
        self._client = client

    async def onboard_agent(
        self,
        agent_name: str,
        email: str,
        *,
        wallet_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StablecoinFinancialAccount:
        """Full onboarding: create connected account + financial account.

        Returns the financial account with USDC deposit address.
        """
        meta = {"wallet_id": wallet_id or "", **(metadata or {})}

        # Step 1: Create connected account
        account = await self._client.create_connected_account(
            business_name=agent_name,
            email=email,
            metadata=meta,
        )

        # Step 2: Create financial account with USDC support
        fa = await self._client.create_financial_account(
            connected_account_id=account["account_id"],
            metadata=meta,
        )

        logger.info(
            "Onboarded agent %s: account=%s, fa=%s, deposit=%s",
            agent_name, account["account_id"], fa.account_id, fa.deposit_address,
        )
        return fa

    async def issue_card(
        self,
        connected_account_id: str,
        *,
        cardholder_name: str,
        cardholder_email: str,
        limit_per_tx: Decimal = Decimal("500"),
        limit_daily: Decimal = Decimal("2000"),
        limit_monthly: Decimal = Decimal("10000"),
        wallet_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a cardholder and issue a stablecoin-backed virtual card.

        Args:
            connected_account_id: The agent's Stripe Connect account
            cardholder_name: Full name for the card
            cardholder_email: Email for the cardholder
            limit_per_tx: Per-transaction spending limit (USD)
            limit_daily: Daily spending limit (USD)
            limit_monthly: Monthly spending limit (USD)
            wallet_id: Optional Sardis wallet ID for metadata

        Returns:
            Dict with card details and cardholder info
        """
        # Create cardholder
        cardholder_id = await self._client.create_cardholder(
            connected_account_id,
            name=cardholder_name,
            email=cardholder_email,
            metadata={"wallet_id": wallet_id or ""},
        )

        # Build spending limits
        spending_limits = []
        if limit_per_tx > 0:
            spending_limits.append({
                "amount": int(limit_per_tx * 100),
                "interval": "per_authorization",
            })
        if limit_daily > 0:
            spending_limits.append({
                "amount": int(limit_daily * 100),
                "interval": "daily",
            })
        if limit_monthly > 0:
            spending_limits.append({
                "amount": int(limit_monthly * 100),
                "interval": "monthly",
            })

        # Issue card
        card = await self._client.create_stablecoin_card(
            connected_account_id,
            cardholder_id,
            spending_limits=spending_limits,
            metadata={"wallet_id": wallet_id or ""},
        )

        return {
            **card,
            "cardholder_id": cardholder_id,
            "limits": {
                "per_tx": str(limit_per_tx),
                "daily": str(limit_daily),
                "monthly": str(limit_monthly),
            },
        }

    async def get_deposit_info(
        self,
        financial_account_id: str,
        connected_account_id: str,
    ) -> dict[str, Any]:
        """Get deposit instructions for funding the account with USDC.

        Returns the Base address where USDC should be sent,
        along with current balance information.
        """
        account = await self._client.get_financial_account(
            financial_account_id, connected_account_id
        )
        return {
            "deposit_address": account.deposit_address,
            "chain": "base",
            "token": "USDC",
            "token_contract": USDC_BASE_CONTRACT,
            "usdc_balance": str(account.usdc_balance),
            "usd_balance": str(account.usd_balance),
            "status": account.status.value,
        }

    async def close(self) -> None:
        await self._client.close()
