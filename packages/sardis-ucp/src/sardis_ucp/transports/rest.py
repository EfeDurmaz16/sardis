"""UCP REST transport layer.

Maps UCP checkout operations to HTTP REST endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from ..capabilities.checkout import UCPCheckoutCapability


class UCPTransport(Protocol):
    """Protocol defining the transport interface for UCP operations."""

    async def create_checkout(self, cart_mandate_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Create a new checkout session.

        Args:
            cart_mandate_id: Identifier for the cart mandate
            **kwargs: Additional parameters for checkout creation

        Returns:
            Dictionary containing checkout session data
        """
        ...

    async def update_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update an existing checkout session.

        Args:
            session_id: Checkout session identifier
            **kwargs: Parameters to update (items, discounts, shipping, etc.)

        Returns:
            Dictionary containing updated checkout session data
        """
        ...

    async def complete_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Complete a checkout session and generate payment mandate.

        Args:
            session_id: Checkout session identifier
            **kwargs: Payment parameters (chain, token, destination, etc.)

        Returns:
            Dictionary containing checkout result and payment mandate
        """
        ...

    async def cancel_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Cancel a checkout session.

        Args:
            session_id: Checkout session identifier
            **kwargs: Additional cancellation parameters

        Returns:
            Dictionary containing cancelled session data
        """
        ...

    async def get_checkout(self, session_id: str) -> Dict[str, Any]:
        """Get a checkout session by ID.

        Args:
            session_id: Checkout session identifier

        Returns:
            Dictionary containing checkout session data
        """
        ...


class UCPRestTransport:
    """REST transport implementation for UCP checkout operations.

    Maps checkout operations to HTTP endpoints:
    - POST /checkout - Create checkout
    - PATCH /checkout/{id} - Update checkout
    - POST /checkout/{id}/complete - Complete checkout
    - DELETE /checkout/{id} - Cancel checkout
    - GET /checkout/{id} - Get checkout
    """

    # HTTP method and path mappings
    ENDPOINT_CREATE = ("POST", "/checkout")
    ENDPOINT_UPDATE = ("PATCH", "/checkout/{session_id}")
    ENDPOINT_COMPLETE = ("POST", "/checkout/{session_id}/complete")
    ENDPOINT_CANCEL = ("DELETE", "/checkout/{session_id}")
    ENDPOINT_GET = ("GET", "/checkout/{session_id}")

    def __init__(
        self,
        base_url: str,
        capability: Optional[UCPCheckoutCapability] = None,
    ) -> None:
        """Initialize REST transport.

        Args:
            base_url: Base URL for the UCP API
            capability: Optional UCPCheckoutCapability instance for local operations
        """
        self._base_url = base_url.rstrip("/")
        self._capability = capability

    async def create_checkout(self, cart_mandate_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Create a new checkout session via POST /checkout.

        Args:
            cart_mandate_id: Identifier for the cart mandate
            **kwargs: Additional parameters (merchant_id, merchant_name, customer_id, etc.)

        Returns:
            Dictionary containing checkout session data
        """
        if self._capability:
            # Delegate to local capability if available
            from ..models.mandates import UCPCurrency, UCPLineItem
            from decimal import Decimal

            session = self._capability.create_checkout(
                merchant_id=kwargs.get("merchant_id", ""),
                merchant_name=kwargs.get("merchant_name", ""),
                merchant_domain=kwargs.get("merchant_domain", ""),
                customer_id=kwargs.get("customer_id", ""),
                line_items=kwargs.get("line_items", []),
                currency=kwargs.get("currency", UCPCurrency.USD),
                tax_rate=kwargs.get("tax_rate"),
                shipping_minor=kwargs.get("shipping_minor", 0),
                metadata=kwargs.get("metadata"),
            )
            return session.to_dict()

        # TODO: Implement HTTP POST request to {base_url}/checkout
        method, path = self.ENDPOINT_CREATE
        url = f"{self._base_url}{path}"
        raise NotImplementedError(f"HTTP transport not yet implemented: {method} {url}")

    async def update_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update a checkout session via PATCH /checkout/{id}.

        Args:
            session_id: Checkout session identifier
            **kwargs: Update parameters (add_items, remove_item_ids, add_discounts, etc.)

        Returns:
            Dictionary containing updated checkout session data
        """
        if self._capability:
            # Delegate to local capability if available
            session = self._capability.update_checkout(
                session_id=session_id,
                add_items=kwargs.get("add_items"),
                remove_item_ids=kwargs.get("remove_item_ids"),
                add_discounts=kwargs.get("add_discounts"),
                remove_discount_ids=kwargs.get("remove_discount_ids"),
                shipping_minor=kwargs.get("shipping_minor"),
                metadata=kwargs.get("metadata"),
            )
            return session.to_dict()

        # TODO: Implement HTTP PATCH request to {base_url}/checkout/{session_id}
        method, path_template = self.ENDPOINT_UPDATE
        path = path_template.format(session_id=session_id)
        url = f"{self._base_url}{path}"
        raise NotImplementedError(f"HTTP transport not yet implemented: {method} {url}")

    async def complete_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Complete a checkout via POST /checkout/{id}/complete.

        Args:
            session_id: Checkout session identifier
            **kwargs: Payment parameters (chain, token, destination, subject, issuer, etc.)

        Returns:
            Dictionary containing checkout result and payment mandate
        """
        if self._capability:
            # Delegate to local capability if available
            result = await self._capability.complete_checkout(
                session_id=session_id,
                chain=kwargs.get("chain", ""),
                token=kwargs.get("token", ""),
                destination=kwargs.get("destination", ""),
                subject=kwargs.get("subject", ""),
                issuer=kwargs.get("issuer", ""),
                execute_payment=kwargs.get("execute_payment", True),
            )
            return result.to_dict()

        # TODO: Implement HTTP POST request to {base_url}/checkout/{session_id}/complete
        method, path_template = self.ENDPOINT_COMPLETE
        path = path_template.format(session_id=session_id)
        url = f"{self._base_url}{path}"
        raise NotImplementedError(f"HTTP transport not yet implemented: {method} {url}")

    async def cancel_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Cancel a checkout via DELETE /checkout/{id}.

        Args:
            session_id: Checkout session identifier
            **kwargs: Additional cancellation parameters

        Returns:
            Dictionary containing cancelled session data
        """
        if self._capability:
            # Delegate to local capability if available
            session = self._capability.cancel_checkout(session_id=session_id)
            return session.to_dict()

        # TODO: Implement HTTP DELETE request to {base_url}/checkout/{session_id}
        method, path_template = self.ENDPOINT_CANCEL
        path = path_template.format(session_id=session_id)
        url = f"{self._base_url}{path}"
        raise NotImplementedError(f"HTTP transport not yet implemented: {method} {url}")

    async def get_checkout(self, session_id: str) -> Dict[str, Any]:
        """Get a checkout session via GET /checkout/{id}.

        Args:
            session_id: Checkout session identifier

        Returns:
            Dictionary containing checkout session data
        """
        if self._capability:
            # Delegate to local capability if available
            session = self._capability.get_checkout(session_id=session_id)
            return session.to_dict()

        # TODO: Implement HTTP GET request to {base_url}/checkout/{session_id}
        method, path_template = self.ENDPOINT_GET
        path = path_template.format(session_id=session_id)
        url = f"{self._base_url}{path}"
        raise NotImplementedError(f"HTTP transport not yet implemented: {method} {url}")


__all__ = [
    "UCPTransport",
    "UCPRestTransport",
]
