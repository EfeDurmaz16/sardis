"""UCP MCP transport layer.

Maps UCP checkout operations to Model Context Protocol (MCP) tool calls.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..capabilities.checkout import UCPCheckoutCapability


class UCPMcpTransport:
    """MCP transport implementation for UCP checkout operations.

    Maps checkout operations to MCP tool calls:
    - {prefix}_create_checkout - Create checkout
    - {prefix}_update_checkout - Update checkout
    - {prefix}_complete_checkout - Complete checkout
    - {prefix}_cancel_checkout - Cancel checkout
    - {prefix}_get_checkout - Get checkout
    """

    # MCP tool definitions with schemas
    TOOL_CREATE_CHECKOUT = {
        "name": "{prefix}_create_checkout",
        "description": "Create a new UCP checkout session with cart items",
        "input_schema": {
            "type": "object",
            "properties": {
                "cart_mandate_id": {
                    "type": "string",
                    "description": "Identifier for the cart mandate",
                },
                "merchant_id": {"type": "string", "description": "Merchant identifier"},
                "merchant_name": {"type": "string", "description": "Merchant display name"},
                "merchant_domain": {"type": "string", "description": "Merchant domain"},
                "customer_id": {"type": "string", "description": "Customer/agent identifier"},
                "line_items": {
                    "type": "array",
                    "description": "Items in the cart",
                    "items": {"type": "object"},
                },
                "currency": {"type": "string", "description": "Currency code (e.g., USD, USDC)"},
                "tax_rate": {"type": "number", "description": "Tax rate as decimal (optional)"},
                "shipping_minor": {"type": "integer", "description": "Shipping cost in minor units"},
                "metadata": {"type": "object", "description": "Additional metadata"},
            },
            "required": ["merchant_id", "merchant_name", "merchant_domain", "customer_id", "line_items"],
        },
        "output_schema": {
            "type": "object",
            "description": "Checkout session data",
        },
    }

    TOOL_UPDATE_CHECKOUT = {
        "name": "{prefix}_update_checkout",
        "description": "Update an existing UCP checkout session",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Checkout session identifier",
                },
                "add_items": {
                    "type": "array",
                    "description": "Items to add to cart",
                    "items": {"type": "object"},
                },
                "remove_item_ids": {
                    "type": "array",
                    "description": "Item IDs to remove",
                    "items": {"type": "string"},
                },
                "add_discounts": {
                    "type": "array",
                    "description": "Discounts to apply",
                    "items": {"type": "object"},
                },
                "remove_discount_ids": {
                    "type": "array",
                    "description": "Discount IDs to remove",
                    "items": {"type": "string"},
                },
                "shipping_minor": {"type": "integer", "description": "Updated shipping cost"},
                "metadata": {"type": "object", "description": "Metadata to merge"},
            },
            "required": ["session_id"],
        },
        "output_schema": {
            "type": "object",
            "description": "Updated checkout session data",
        },
    }

    TOOL_COMPLETE_CHECKOUT = {
        "name": "{prefix}_complete_checkout",
        "description": "Complete a UCP checkout session and generate payment mandate",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Checkout session identifier",
                },
                "chain": {"type": "string", "description": "Blockchain network (e.g., base, polygon)"},
                "token": {"type": "string", "description": "Token symbol (e.g., USDC, USDT)"},
                "destination": {"type": "string", "description": "Recipient address"},
                "subject": {"type": "string", "description": "Payer identifier"},
                "issuer": {"type": "string", "description": "Platform identifier"},
                "execute_payment": {
                    "type": "boolean",
                    "description": "Whether to execute payment immediately",
                    "default": True,
                },
            },
            "required": ["session_id", "chain", "token", "destination", "subject", "issuer"],
        },
        "output_schema": {
            "type": "object",
            "description": "Checkout result with payment mandate",
        },
    }

    TOOL_CANCEL_CHECKOUT = {
        "name": "{prefix}_cancel_checkout",
        "description": "Cancel a UCP checkout session",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Checkout session identifier",
                },
            },
            "required": ["session_id"],
        },
        "output_schema": {
            "type": "object",
            "description": "Cancelled checkout session data",
        },
    }

    TOOL_GET_CHECKOUT = {
        "name": "{prefix}_get_checkout",
        "description": "Get a UCP checkout session by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Checkout session identifier",
                },
            },
            "required": ["session_id"],
        },
        "output_schema": {
            "type": "object",
            "description": "Checkout session data",
        },
    }

    def __init__(
        self,
        tool_prefix: str = "sardis",
        capability: Optional[UCPCheckoutCapability] = None,
    ) -> None:
        """Initialize MCP transport.

        Args:
            tool_prefix: Prefix for MCP tool names (e.g., "sardis" -> "sardis_create_checkout")
            capability: Optional UCPCheckoutCapability instance for local operations
        """
        self._tool_prefix = tool_prefix
        self._capability = capability

    def get_tool_name(self, base_name: str) -> str:
        """Get the full tool name with prefix.

        Args:
            base_name: Base tool name (e.g., "create_checkout")

        Returns:
            Full tool name with prefix (e.g., "sardis_create_checkout")
        """
        return f"{self._tool_prefix}_{base_name}"

    def get_tool_schemas(self) -> list[Dict[str, Any]]:
        """Get all MCP tool schemas with the configured prefix.

        Returns:
            List of tool schema dictionaries
        """
        schemas = [
            self.TOOL_CREATE_CHECKOUT,
            self.TOOL_UPDATE_CHECKOUT,
            self.TOOL_COMPLETE_CHECKOUT,
            self.TOOL_CANCEL_CHECKOUT,
            self.TOOL_GET_CHECKOUT,
        ]

        # Apply prefix to tool names
        return [
            {
                **schema,
                "name": schema["name"].format(prefix=self._tool_prefix),
            }
            for schema in schemas
        ]

    async def create_checkout(self, cart_mandate_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Create a new checkout session via MCP tool call.

        Args:
            cart_mandate_id: Identifier for the cart mandate
            **kwargs: Additional parameters (merchant_id, merchant_name, customer_id, etc.)

        Returns:
            Dictionary containing checkout session data
        """
        if self._capability:
            # Delegate to local capability if available
            from ..models.mandates import UCPCurrency

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

        tool_name = self.get_tool_name("create_checkout")
        raise NotImplementedError(
            f"MCP tool call requires an MCP client connection. "
            f"Use the local capability constructor or configure an MCP client for: {tool_name}"
        )

    async def update_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update a checkout session via MCP tool call.

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

        tool_name = self.get_tool_name("update_checkout")
        raise NotImplementedError(
            f"MCP tool call requires an MCP client connection. "
            f"Use the local capability constructor or configure an MCP client for: {tool_name}"
        )

    async def complete_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Complete a checkout via MCP tool call.

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

        tool_name = self.get_tool_name("complete_checkout")
        raise NotImplementedError(
            f"MCP tool call requires an MCP client connection. "
            f"Use the local capability constructor or configure an MCP client for: {tool_name}"
        )

    async def cancel_checkout(self, session_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Cancel a checkout via MCP tool call.

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

        tool_name = self.get_tool_name("cancel_checkout")
        raise NotImplementedError(
            f"MCP tool call requires an MCP client connection. "
            f"Use the local capability constructor or configure an MCP client for: {tool_name}"
        )

    async def get_checkout(self, session_id: str) -> Dict[str, Any]:
        """Get a checkout session via MCP tool call.

        Args:
            session_id: Checkout session identifier

        Returns:
            Dictionary containing checkout session data
        """
        if self._capability:
            # Delegate to local capability if available
            session = self._capability.get_checkout(session_id=session_id)
            return session.to_dict()

        tool_name = self.get_tool_name("get_checkout")
        raise NotImplementedError(
            f"MCP tool call requires an MCP client connection. "
            f"Use the local capability constructor or configure an MCP client for: {tool_name}"
        )


__all__ = [
    "UCPMcpTransport",
]
