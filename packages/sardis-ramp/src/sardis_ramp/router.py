"""RampRouter - Intelligent provider selection and fallback."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Literal, Optional

from .base import RampProvider, RampQuote, RampSession

logger = logging.getLogger(__name__)


class RampRouter:
    """
    Intelligent routing for fiat ramp operations.

    Features:
    - Auto-selects best provider based on token, direction, fees
    - Fallback chain: primary fails → try next provider
    - Compare quotes across providers

    Selection logic:
    1. USDC on-ramp → Coinbase (0% fee)
    2. Other tokens on-ramp → Bridge
    3. Any off-ramp → Bridge (Coinbase doesn't support)
    """

    def __init__(self, providers: list[RampProvider]):
        """
        Initialize the router with available providers.

        Args:
            providers: List of RampProvider instances to route between
        """
        if not providers:
            raise ValueError("At least one provider required")

        self._providers = providers
        self._provider_map = {p.provider_name: p for p in providers}

    async def get_best_onramp(
        self,
        amount_fiat: Decimal,
        fiat_currency: str,
        crypto_currency: str,
        chain: str,
        destination_address: str,
        wallet_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        preferred_provider: Optional[str] = None,
    ) -> RampSession:
        """
        Create on-ramp with the best provider.

        Selection priority:
        1. Preferred provider (if specified and supports on-ramp)
        2. USDC → Coinbase (0% fee)
        3. Other tokens → Bridge or first available

        Falls back to next provider on failure.

        Args:
            amount_fiat: Amount of fiat to spend
            fiat_currency: Fiat currency (USD, EUR, etc.)
            crypto_currency: Crypto to receive (USDC, USDT, etc.)
            chain: Destination blockchain
            destination_address: Address to receive crypto
            wallet_id: Optional Sardis wallet ID
            metadata: Optional metadata
            preferred_provider: Optional provider name to prefer

        Returns:
            RampSession from the selected provider

        Raises:
            ValueError: If no provider can handle the request
        """
        # Filter providers that support on-ramp
        onramp_providers = [p for p in self._providers if p.supports_onramp]

        if not onramp_providers:
            raise ValueError("No providers support on-ramp")

        # Determine priority order
        provider_priority = self._get_onramp_priority(
            crypto_currency=crypto_currency,
            preferred_provider=preferred_provider,
            available_providers=onramp_providers,
        )

        # Try providers in order until one succeeds
        last_error = None
        for provider in provider_priority:
            try:
                logger.info(
                    f"Attempting on-ramp with {provider.provider_name}: "
                    f"{amount_fiat} {fiat_currency} → {crypto_currency} on {chain}"
                )
                session = await provider.create_onramp(
                    amount_fiat=amount_fiat,
                    fiat_currency=fiat_currency,
                    crypto_currency=crypto_currency,
                    chain=chain,
                    destination_address=destination_address,
                    wallet_id=wallet_id,
                    metadata=metadata,
                )
                logger.info(f"On-ramp session created: {session.session_id} via {provider.provider_name}")
                return session

            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider.provider_name} failed: {e}")
                continue

        # All providers failed
        raise ValueError(f"All on-ramp providers failed. Last error: {last_error}")

    async def get_best_offramp(
        self,
        amount_crypto: Decimal,
        crypto_currency: str,
        chain: str,
        fiat_currency: str,
        bank_account: dict,
        wallet_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        preferred_provider: Optional[str] = None,
    ) -> RampSession:
        """
        Create off-ramp with the best provider.

        Currently only Bridge supports off-ramp.

        Args:
            amount_crypto: Amount of crypto to sell
            crypto_currency: Crypto to sell (USDC, USDT, etc.)
            chain: Source blockchain
            fiat_currency: Fiat to receive (USD, EUR, etc.)
            bank_account: Bank account for payout
            wallet_id: Optional Sardis wallet ID
            metadata: Optional metadata
            preferred_provider: Optional provider name to prefer

        Returns:
            RampSession from the selected provider

        Raises:
            ValueError: If no provider supports off-ramp
        """
        # Filter providers that support off-ramp
        offramp_providers = [p for p in self._providers if p.supports_offramp]

        if not offramp_providers:
            raise ValueError("No providers support off-ramp")

        # Use preferred provider if specified, otherwise use first available
        if preferred_provider and preferred_provider in self._provider_map:
            provider = self._provider_map[preferred_provider]
            if not provider.supports_offramp:
                raise ValueError(f"Provider {preferred_provider} does not support off-ramp")
        else:
            provider = offramp_providers[0]

        logger.info(
            f"Creating off-ramp with {provider.provider_name}: "
            f"{amount_crypto} {crypto_currency} → {fiat_currency}"
        )

        return await provider.create_offramp(
            amount_crypto=amount_crypto,
            crypto_currency=crypto_currency,
            chain=chain,
            fiat_currency=fiat_currency,
            bank_account=bank_account,
            wallet_id=wallet_id,
            metadata=metadata,
        )

    async def get_all_quotes(
        self,
        amount: Decimal,
        source_currency: str,
        destination_currency: str,
        chain: str,
        direction: Literal["onramp", "offramp"],
    ) -> list[RampQuote]:
        """
        Get quotes from all providers that support the operation.

        Args:
            amount: Amount in source currency
            source_currency: Source currency code
            destination_currency: Destination currency code
            chain: Blockchain network
            direction: "onramp" or "offramp"

        Returns:
            List of RampQuote objects, sorted by best rate (lowest fee)
        """
        quotes = []

        for provider in self._providers:
            # Skip providers that don't support the direction
            if direction == "onramp" and not provider.supports_onramp:
                continue
            if direction == "offramp" and not provider.supports_offramp:
                continue

            try:
                quote = await provider.get_quote(
                    amount=amount,
                    source_currency=source_currency,
                    destination_currency=destination_currency,
                    chain=chain,
                    direction=direction,
                )
                quotes.append(quote)
            except Exception as e:
                logger.warning(f"Failed to get quote from {provider.provider_name}: {e}")
                continue

        # Sort by fee (lowest first)
        quotes.sort(key=lambda q: q.fee_percent)

        return quotes

    async def get_status(self, session_id: str, provider_name: str) -> RampSession:
        """
        Get status of a ramp session.

        Args:
            session_id: The session ID
            provider_name: The provider that created the session

        Returns:
            Updated RampSession

        Raises:
            ValueError: If provider not found
        """
        if provider_name not in self._provider_map:
            raise ValueError(f"Unknown provider: {provider_name}")

        provider = self._provider_map[provider_name]
        return await provider.get_status(session_id)

    def _get_onramp_priority(
        self,
        crypto_currency: str,
        preferred_provider: Optional[str],
        available_providers: list[RampProvider],
    ) -> list[RampProvider]:
        """
        Determine provider priority for on-ramp.

        Priority:
        1. Preferred provider (if specified)
        2. USDC → Coinbase (0% fee)
        3. Other → Bridge or first available
        """
        providers = available_providers.copy()

        # If preferred provider specified, put it first
        if preferred_provider:
            preferred = next(
                (p for p in providers if p.provider_name == preferred_provider),
                None
            )
            if preferred:
                providers.remove(preferred)
                providers.insert(0, preferred)
                return providers

        # Smart routing based on token
        if crypto_currency.upper() == "USDC":
            # USDC: prefer Coinbase for 0% fee
            coinbase = next((p for p in providers if p.provider_name == "coinbase"), None)
            if coinbase:
                providers.remove(coinbase)
                providers.insert(0, coinbase)

        return providers

    async def close(self):
        """Close all provider connections."""
        for provider in self._providers:
            await provider.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
