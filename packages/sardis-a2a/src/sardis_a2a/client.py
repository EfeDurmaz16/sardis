"""A2A client for outbound agent communication.

Provides methods for sending A2A messages to other agents:
- Payment requests
- Credential verification
- Checkout flows
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

from .messages import (
    A2AMessage,
    A2AMessageType,
    A2AMessageStatus,
    A2APaymentRequest,
    A2APaymentResponse,
    A2ACredentialRequest,
    A2ACredentialResponse,
)
from .discovery import AgentDiscoveryService, DiscoveredAgent

logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Error during A2A client operations."""

    def __init__(
        self,
        message: str,
        code: str,
        recipient_id: str | None = None,
        details: Dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.recipient_id = recipient_id
        self.details = details or {}


class HttpClient(Protocol):
    """Protocol for HTTP client operations."""

    async def post(
        self,
        url: str,
        json: Dict[str, Any],
        headers: Dict[str, str] | None = None,
    ) -> tuple[int, Dict[str, Any]]:
        """Make an HTTP POST request.

        Returns:
            Tuple of (status_code, json_response)
        """
        ...


class MessageSigner(Protocol):
    """Protocol for signing A2A messages."""

    def sign(self, message: A2AMessage) -> str:
        """Sign a message and return the signature."""
        ...

    def verify(self, message: A2AMessage, signature: str) -> bool:
        """Verify a message signature."""
        ...


@dataclass
class A2AClientConfig:
    """Configuration for A2A client."""

    # Client identity
    agent_id: str
    agent_name: str

    # Endpoints
    base_url: str  # Our base URL for callbacks

    # Signing
    signing_key_id: Optional[str] = None
    private_key: Optional[str] = None

    # Timeouts (seconds)
    request_timeout: int = 30
    message_ttl: int = 300  # 5 minutes

    # Retries
    max_retries: int = 3
    retry_delay: float = 1.0


class A2AClient:
    """
    Client for A2A inter-agent communication.

    Provides methods for:
    - Sending payment requests to other agents
    - Verifying credentials with other agents
    - General A2A message exchange

    Uses agent discovery to find agent endpoints.
    """

    def __init__(
        self,
        config: A2AClientConfig,
        http_client: HttpClient | None = None,
        discovery: AgentDiscoveryService | None = None,
        signer: MessageSigner | None = None,
    ) -> None:
        """
        Initialize the A2A client.

        Args:
            config: Client configuration
            http_client: HTTP client for requests
            discovery: Agent discovery service
            signer: Message signer for authentication
        """
        self._config = config
        self._http_client = http_client
        self._discovery = discovery or AgentDiscoveryService()
        self._signer = signer

    @property
    def agent_id(self) -> str:
        """Our agent ID."""
        return self._config.agent_id

    async def send_payment_request(
        self,
        recipient_url: str,
        amount_minor: int,
        token: str,
        chain: str,
        destination: str,
        purpose: str = "",
        reference: str | None = None,
        callback_url: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> A2APaymentResponse:
        """
        Send a payment request to another agent.

        Args:
            recipient_url: Base URL of the recipient agent
            amount_minor: Amount in minor units
            token: Token symbol (e.g., "USDC")
            chain: Blockchain network (e.g., "base")
            destination: Payment destination address
            purpose: Purpose of the payment
            reference: External reference (order ID, invoice, etc.)
            callback_url: URL for payment status callbacks
            metadata: Additional metadata

        Returns:
            A2APaymentResponse with result

        Raises:
            A2AClientError: If request fails
        """
        # Discover recipient
        recipient = await self._discovery.discover_agent(recipient_url)

        if not recipient.available:
            raise A2AClientError(
                f"Recipient agent not available: {recipient.last_error}",
                code="agent_unavailable",
                recipient_id=recipient.agent_id,
            )

        # Check capabilities
        if not recipient.supports_payment(token, chain):
            raise A2AClientError(
                f"Recipient does not support {token} on {chain}",
                code="unsupported_payment",
                recipient_id=recipient.agent_id,
            )

        # Build request
        request = A2APaymentRequest(
            sender_agent_id=self._config.agent_id,
            recipient_agent_id=recipient.agent_id,
            amount_minor=amount_minor,
            token=token,
            chain=chain,
            destination=destination,
            purpose=purpose,
            reference=reference,
            callback_url=callback_url or f"{self._config.base_url}/api/v2/a2a/callback",
            metadata=metadata or {},
        )

        # Convert to A2A message
        message = request.to_a2a_message()

        # Sign if signer available
        if self._signer:
            message.signature = self._signer.sign(message)

        # Send request
        response = await self._send_message(recipient, message)

        # Parse response
        if response.message_type == A2AMessageType.PAYMENT_RESPONSE:
            payload = response.payload
            return A2APaymentResponse(
                response_id=payload.get("response_id", response.message_id),
                request_id=request.request_id,
                sender_agent_id=response.sender_id,
                recipient_agent_id=response.recipient_id,
                success=payload.get("success", False),
                status=payload.get("status", "unknown"),
                tx_hash=payload.get("tx_hash"),
                chain=payload.get("chain"),
                block_number=payload.get("block_number"),
                error=payload.get("error") or response.error,
                error_code=payload.get("error_code") or response.error_code,
                metadata=payload.get("metadata", {}),
            )
        elif response.message_type == A2AMessageType.ERROR:
            return A2APaymentResponse(
                request_id=request.request_id,
                sender_agent_id=response.sender_id,
                recipient_agent_id=response.recipient_id,
                success=False,
                status="failed",
                error=response.error or "Unknown error",
                error_code=response.error_code or "unknown_error",
            )
        else:
            raise A2AClientError(
                f"Unexpected response type: {response.message_type}",
                code="unexpected_response",
                recipient_id=recipient.agent_id,
            )

    async def verify_credential(
        self,
        recipient_url: str,
        credential_type: str,
        credential_data: Dict[str, Any],
        verify_signature: bool = True,
        verify_expiration: bool = True,
        verify_chain: bool = True,
    ) -> A2ACredentialResponse:
        """
        Request credential verification from another agent.

        Args:
            recipient_url: Base URL of the verifying agent
            credential_type: Type of credential (mandate, identity, etc.)
            credential_data: The credential data to verify
            verify_signature: Whether to verify signatures
            verify_expiration: Whether to check expiration
            verify_chain: Whether to verify mandate chain

        Returns:
            A2ACredentialResponse with verification result

        Raises:
            A2AClientError: If request fails
        """
        # Discover recipient
        recipient = await self._discovery.discover_agent(recipient_url)

        if not recipient.available:
            raise A2AClientError(
                f"Recipient agent not available: {recipient.last_error}",
                code="agent_unavailable",
                recipient_id=recipient.agent_id,
            )

        # Build request
        request = A2ACredentialRequest(
            sender_agent_id=self._config.agent_id,
            recipient_agent_id=recipient.agent_id,
            credential_type=credential_type,
            credential_data=credential_data,
            verify_signature=verify_signature,
            verify_expiration=verify_expiration,
            verify_chain=verify_chain,
        )

        # Convert to A2A message
        message = request.to_a2a_message()

        # Sign if signer available
        if self._signer:
            message.signature = self._signer.sign(message)

        # Send request
        response = await self._send_message(recipient, message)

        # Parse response
        if response.message_type == A2AMessageType.CREDENTIAL_RESPONSE:
            payload = response.payload
            return A2ACredentialResponse(
                response_id=payload.get("response_id", response.message_id),
                request_id=request.request_id,
                sender_agent_id=response.sender_id,
                recipient_agent_id=response.recipient_id,
                valid=payload.get("valid", False),
                signature_valid=payload.get("signature_valid"),
                not_expired=payload.get("not_expired"),
                chain_valid=payload.get("chain_valid"),
                error=payload.get("error") or response.error,
                error_code=payload.get("error_code") or response.error_code,
                verification_details=payload.get("verification_details", {}),
            )
        elif response.message_type == A2AMessageType.ERROR:
            return A2ACredentialResponse(
                request_id=request.request_id,
                sender_agent_id=response.sender_id,
                recipient_agent_id=response.recipient_id,
                valid=False,
                error=response.error or "Unknown error",
                error_code=response.error_code or "unknown_error",
            )
        else:
            raise A2AClientError(
                f"Unexpected response type: {response.message_type}",
                code="unexpected_response",
                recipient_id=recipient.agent_id,
            )

    async def send_message(
        self,
        recipient_url: str,
        message: A2AMessage,
    ) -> A2AMessage:
        """
        Send a raw A2A message to another agent.

        Args:
            recipient_url: Base URL of the recipient agent
            message: Message to send

        Returns:
            Response message

        Raises:
            A2AClientError: If request fails
        """
        # Discover recipient
        recipient = await self._discovery.discover_agent(recipient_url)

        if not recipient.available:
            raise A2AClientError(
                f"Recipient agent not available: {recipient.last_error}",
                code="agent_unavailable",
                recipient_id=recipient.agent_id,
            )

        # Update sender ID
        message.sender_id = self._config.agent_id

        # Sign if signer available
        if self._signer and not message.signature:
            message.signature = self._signer.sign(message)

        return await self._send_message(recipient, message)

    async def _send_message(
        self,
        recipient: DiscoveredAgent,
        message: A2AMessage,
    ) -> A2AMessage:
        """Send a message to a discovered agent."""
        if self._http_client is None:
            raise A2AClientError(
                "HTTP client not configured",
                code="client_not_configured",
                recipient_id=recipient.agent_id,
            )

        # Determine A2A endpoint
        a2a_url = f"{recipient.agent_url}/api/v2/a2a/messages"
        if recipient.card and recipient.card.a2a_endpoint:
            a2a_url = recipient.card.a2a_endpoint.url

        logger.info(
            f"Sending A2A message: type={message.message_type.value}, "
            f"recipient={recipient.agent_id}, url={a2a_url}"
        )

        try:
            status, data = await self._http_client.post(
                a2a_url,
                json=message.to_dict(),
                headers={
                    "Content-Type": "application/json",
                    "X-Sardis-Agent-Id": self._config.agent_id,
                },
            )

            if status >= 400:
                raise A2AClientError(
                    f"HTTP {status} from {a2a_url}",
                    code=f"http_{status}",
                    recipient_id=recipient.agent_id,
                    details={"response": data},
                )

            # Parse response
            response = A2AMessage.from_dict(data)

            logger.info(
                f"Received A2A response: type={response.message_type.value}, "
                f"status={response.status.value}"
            )

            return response

        except A2AClientError:
            raise
        except Exception as e:
            logger.error(f"A2A message send failed: {e}")
            raise A2AClientError(
                f"Failed to send message: {e}",
                code="send_failed",
                recipient_id=recipient.agent_id,
                details={"error": str(e)},
            )


__all__ = [
    "A2AClientError",
    "HttpClient",
    "MessageSigner",
    "A2AClientConfig",
    "A2AClient",
]
