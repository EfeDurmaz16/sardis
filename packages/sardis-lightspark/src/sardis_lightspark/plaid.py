"""Plaid Link integration for Grid bank account linking."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from .client import GridClient
from .models import PlaidLinkToken

logger = logging.getLogger(__name__)


class PlaidService:
    """
    Plaid Link integration via Lightspark Grid.

    Flow:
    1. create_link_token() → get Plaid Link token for frontend
    2. User completes Plaid Link in frontend
    3. exchange_public_token() → exchange for access token
    4. get_bank_account() → get linked bank account details
    """

    def __init__(self, client: GridClient):
        self._client = client

    async def create_link_token(
        self,
        customer_id: str,
        redirect_uri: str | None = None,
    ) -> PlaidLinkToken:
        """
        Create a Plaid Link token for the frontend.

        Args:
            customer_id: Grid customer ID
            redirect_uri: Optional redirect URI after completion

        Returns:
            PlaidLinkToken with link_token and expiration
        """
        body: dict = {"customerId": customer_id}
        if redirect_uri:
            body["redirectUri"] = redirect_uri

        result = await self._client.request("POST", "/plaid/link-token", body)

        return PlaidLinkToken(
            link_token=result.get("linkToken", ""),
            expiration=datetime.now(UTC) + timedelta(hours=4),
            request_id=result.get("requestId", ""),
        )

    async def exchange_public_token(
        self,
        customer_id: str,
        public_token: str,
    ) -> dict:
        """
        Exchange Plaid public token for access token.

        Called after user completes Plaid Link.

        Args:
            customer_id: Grid customer ID
            public_token: Plaid public token from frontend

        Returns:
            Dict with account details
        """
        return await self._client.request(
            "POST",
            "/plaid/exchange",
            {
                "customerId": customer_id,
                "publicToken": public_token,
            },
        )

    async def get_bank_account(self, customer_id: str) -> dict | None:
        """Get linked bank account details for a customer."""
        try:
            return await self._client.request(
                "GET", f"/plaid/accounts/{customer_id}"
            )
        except Exception:
            return None
