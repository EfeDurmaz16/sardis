"""Tests for A2A client."""

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from sardis_a2a.agent_card import (
    AgentCapability,
    PaymentCapability,
    SardisAgentCard,
    ServiceEndpoint,
)
from sardis_a2a.messages import (
    A2AMessage,
    A2AMessageType,
    A2AMessageStatus,
)
from sardis_a2a.discovery import (
    DiscoveredAgent,
    AgentDiscoveryService,
)
from sardis_a2a.client import (
    A2AClient,
    A2AClientConfig,
    A2AClientError,
)


class MockHttpClient:
    """Mock HTTP client for testing."""

    def __init__(self):
        self.get_responses: Dict[str, tuple[int, Dict[str, Any]]] = {}
        self.post_responses: Dict[str, tuple[int, Dict[str, Any]]] = {}
        self.post_calls: list[tuple[str, Dict[str, Any]]] = []

    def add_get_response(self, url: str, status: int, data: Dict[str, Any]):
        """Add a mock GET response."""
        self.get_responses[url] = (status, data)

    def add_post_response(self, url: str, status: int, data: Dict[str, Any]):
        """Add a mock POST response."""
        self.post_responses[url] = (status, data)

    async def get(
        self, url: str, headers: Dict[str, str] | None = None
    ) -> tuple[int, Dict[str, Any]]:
        """Mock GET request."""
        if url in self.get_responses:
            return self.get_responses[url]
        return 404, {"error": "Not found"}

    async def post(
        self,
        url: str,
        json: Dict[str, Any],
        headers: Dict[str, str] | None = None,
    ) -> tuple[int, Dict[str, Any]]:
        """Mock POST request."""
        self.post_calls.append((url, json))
        if url in self.post_responses:
            return self.post_responses[url]
        return 404, {"error": "Not found"}


class MockSigner:
    """Mock message signer for testing."""

    def sign(self, message: A2AMessage) -> str:
        """Return a mock signature."""
        return f"mock_sig_{message.message_id[:8]}"

    def verify(self, message: A2AMessage, signature: str) -> bool:
        """Verify signature matches our mock format."""
        return signature.startswith("mock_sig_")


class TestA2AClientError:
    """Tests for A2AClientError."""

    def test_create_error(self):
        """Test creating an A2A client error."""
        error = A2AClientError(
            message="Connection failed",
            code="connection_error",
            recipient_id="agent_123",
            details={"host": "example.com"},
        )

        assert str(error) == "Connection failed"
        assert error.code == "connection_error"
        assert error.recipient_id == "agent_123"
        assert error.details["host"] == "example.com"

    def test_error_without_details(self):
        """Test error without optional fields."""
        error = A2AClientError("Error", code="generic")

        assert error.recipient_id is None
        assert error.details == {}


class TestA2AClientConfig:
    """Tests for A2AClientConfig."""

    def test_create_config(self):
        """Test creating client config."""
        config = A2AClientConfig(
            agent_id="agent_sender",
            agent_name="Sender Agent",
            base_url="https://sender.example.com",
        )

        assert config.agent_id == "agent_sender"
        assert config.agent_name == "Sender Agent"
        assert config.base_url == "https://sender.example.com"

    def test_default_values(self):
        """Test default config values."""
        config = A2AClientConfig(
            agent_id="agent_1",
            agent_name="Agent",
            base_url="https://example.com",
        )

        assert config.request_timeout == 30
        assert config.message_ttl == 300
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_custom_values(self):
        """Test custom config values."""
        config = A2AClientConfig(
            agent_id="agent_1",
            agent_name="Agent",
            base_url="https://example.com",
            signing_key_id="key_123",
            private_key="private_key_data",
            request_timeout=60,
            message_ttl=600,
        )

        assert config.signing_key_id == "key_123"
        assert config.request_timeout == 60
        assert config.message_ttl == 600


class TestA2AClient:
    """Tests for A2AClient."""

    @pytest.fixture
    def http_client(self):
        """Create a mock HTTP client."""
        return MockHttpClient()

    @pytest.fixture
    def config(self):
        """Create a client config."""
        return A2AClientConfig(
            agent_id="agent_sender",
            agent_name="Sender Agent",
            base_url="https://sender.example.com",
        )

    @pytest.fixture
    def recipient_card(self):
        """Create a sample recipient agent card."""
        return SardisAgentCard(
            agent_id="agent_recipient",
            agent_name="Recipient Agent",
            capabilities=[
                AgentCapability.PAYMENT_EXECUTE,
                AgentCapability.PAYMENT_VERIFY,
            ],
            payment_capability=PaymentCapability(
                supported_tokens=["USDC", "USDT"],
                supported_chains=["base", "polygon"],
            ),
            a2a_endpoint=ServiceEndpoint(
                url="https://recipient.example.com/api/v2/a2a/messages",
            ),
        )

    @pytest.fixture
    def agent_card_data(self, recipient_card):
        """Agent card JSON data."""
        return recipient_card.to_dict()

    @pytest.fixture
    def discovery(self, http_client, agent_card_data):
        """Create discovery service with mock responses."""
        http_client.add_get_response(
            "https://recipient.example.com/.well-known/agent-card.json",
            200,
            agent_card_data,
        )
        return AgentDiscoveryService(http_client=http_client)

    @pytest.fixture
    def client(self, config, http_client, discovery):
        """Create an A2A client."""
        return A2AClient(
            config=config,
            http_client=http_client,
            discovery=discovery,
        )

    def test_create_client(self, client, config):
        """Test creating a client."""
        assert client.agent_id == "agent_sender"

    @pytest.mark.asyncio
    async def test_send_payment_request_success(self, client, http_client):
        """Test successful payment request."""
        # Mock successful payment response
        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            200,
            {
                "message_id": "resp_123",
                "message_type": "payment_response",
                "sender_id": "agent_recipient",
                "recipient_id": "agent_sender",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "payload": {
                    "response_id": "resp_123",
                    "request_id": "req_123",
                    "success": True,
                    "status": "confirmed",
                    "tx_hash": "0xabcdef123456",
                    "chain": "base",
                    "block_number": 12345,
                },
            },
        )

        response = await client.send_payment_request(
            recipient_url="https://recipient.example.com",
            amount_minor=5000,
            token="USDC",
            chain="base",
            destination="0x1234567890abcdef1234567890abcdef12345678",
            purpose="Test payment",
        )

        assert response.success is True
        assert response.status == "confirmed"
        assert response.tx_hash == "0xabcdef123456"
        assert response.chain == "base"
        assert response.block_number == 12345

    @pytest.mark.asyncio
    async def test_send_payment_request_failure(self, client, http_client):
        """Test failed payment request."""
        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            200,
            {
                "message_id": "resp_123",
                "message_type": "payment_response",
                "sender_id": "agent_recipient",
                "recipient_id": "agent_sender",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "payload": {
                    "success": False,
                    "status": "failed",
                    "error": "Insufficient balance",
                    "error_code": "insufficient_balance",
                },
            },
        )

        response = await client.send_payment_request(
            recipient_url="https://recipient.example.com",
            amount_minor=1_000_000_00,  # $1M
            token="USDC",
            chain="base",
            destination="0x1234567890abcdef1234567890abcdef12345678",
        )

        assert response.success is False
        assert response.error == "Insufficient balance"
        assert response.error_code == "insufficient_balance"

    @pytest.mark.asyncio
    async def test_send_payment_request_unsupported_payment(self, client):
        """Test payment request with unsupported token/chain."""
        with pytest.raises(A2AClientError) as exc_info:
            await client.send_payment_request(
                recipient_url="https://recipient.example.com",
                amount_minor=5000,
                token="UNKNOWN",  # Not supported
                chain="base",
                destination="0x1234",
            )

        assert exc_info.value.code == "unsupported_payment"

    @pytest.mark.asyncio
    async def test_send_payment_request_agent_unavailable(self, config, http_client):
        """Test payment request to unavailable agent."""
        # Discovery will fail - no mock response added
        discovery = AgentDiscoveryService(http_client=http_client)
        client = A2AClient(config=config, http_client=http_client, discovery=discovery)

        with pytest.raises(A2AClientError) as exc_info:
            await client.send_payment_request(
                recipient_url="https://unavailable.example.com",
                amount_minor=5000,
                token="USDC",
                chain="base",
                destination="0x1234",
            )

        assert exc_info.value.code == "agent_unavailable"

    @pytest.mark.asyncio
    async def test_send_payment_request_with_metadata(self, client, http_client):
        """Test payment request with metadata."""
        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            200,
            {
                "message_id": "resp_123",
                "message_type": "payment_response",
                "sender_id": "agent_recipient",
                "recipient_id": "agent_sender",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "payload": {
                    "success": True,
                    "status": "confirmed",
                    "tx_hash": "0xabc",
                },
            },
        )

        await client.send_payment_request(
            recipient_url="https://recipient.example.com",
            amount_minor=5000,
            token="USDC",
            chain="base",
            destination="0x1234567890abcdef1234567890abcdef12345678",
            reference="order_123",
            metadata={"order_id": "123", "customer_id": "cust_456"},
        )

        # Check that metadata was included in request
        assert len(http_client.post_calls) == 1
        _, sent_data = http_client.post_calls[0]
        assert sent_data["payload"]["reference"] == "order_123"
        assert sent_data["payload"]["metadata"]["order_id"] == "123"

    @pytest.mark.asyncio
    async def test_verify_credential_success(self, client, http_client):
        """Test successful credential verification."""
        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            200,
            {
                "message_id": "resp_123",
                "message_type": "credential_response",
                "sender_id": "agent_recipient",
                "recipient_id": "agent_sender",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "payload": {
                    "valid": True,
                    "signature_valid": True,
                    "not_expired": True,
                    "chain_valid": True,
                    "verification_details": {"verified_at": "2024-01-15T10:00:00Z"},
                },
            },
        )

        response = await client.verify_credential(
            recipient_url="https://recipient.example.com",
            credential_type="mandate",
            credential_data={"mandate_id": "mand_123"},
        )

        assert response.valid is True
        assert response.signature_valid is True
        assert response.not_expired is True
        assert response.chain_valid is True

    @pytest.mark.asyncio
    async def test_verify_credential_invalid(self, client, http_client):
        """Test invalid credential verification."""
        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            200,
            {
                "message_id": "resp_123",
                "message_type": "credential_response",
                "sender_id": "agent_recipient",
                "recipient_id": "agent_sender",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "payload": {
                    "valid": False,
                    "signature_valid": False,
                    "error": "Invalid signature",
                    "error_code": "invalid_signature",
                },
            },
        )

        response = await client.verify_credential(
            recipient_url="https://recipient.example.com",
            credential_type="mandate",
            credential_data={"mandate_id": "mand_invalid"},
        )

        assert response.valid is False
        assert response.signature_valid is False
        assert response.error == "Invalid signature"

    @pytest.mark.asyncio
    async def test_send_message_raw(self, client, http_client):
        """Test sending raw A2A message."""
        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            200,
            {
                "message_id": "resp_123",
                "message_type": "ack",
                "sender_id": "agent_recipient",
                "recipient_id": "agent_sender",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "received",
                "payload": {},
            },
        )

        message = A2AMessage(
            message_type=A2AMessageType.ACK,
            recipient_id="agent_recipient",
            payload={"data": "test"},
        )

        response = await client.send_message(
            recipient_url="https://recipient.example.com",
            message=message,
        )

        assert response.message_type == A2AMessageType.ACK
        assert response.status == A2AMessageStatus.RECEIVED

    @pytest.mark.asyncio
    async def test_send_message_no_http_client(self, config, discovery):
        """Test sending message without HTTP client."""
        client = A2AClient(
            config=config,
            http_client=None,  # No HTTP client
            discovery=discovery,
        )

        # Pre-register agent so discovery doesn't need HTTP
        discovery.register_agent(
            agent_id="agent_recipient",
            agent_name="Recipient",
            agent_url="https://recipient.example.com",
            card=SardisAgentCard(
                agent_id="agent_recipient",
                agent_name="Recipient",
            ),
        )

        with pytest.raises(A2AClientError) as exc_info:
            await client.send_message(
                recipient_url="https://recipient.example.com",
                message=A2AMessage(),
            )

        assert exc_info.value.code == "client_not_configured"

    @pytest.mark.asyncio
    async def test_send_message_http_error(self, client, http_client):
        """Test handling HTTP error response."""
        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            500,
            {"error": "Internal server error"},
        )

        with pytest.raises(A2AClientError) as exc_info:
            await client.send_message(
                recipient_url="https://recipient.example.com",
                message=A2AMessage(),
            )

        assert exc_info.value.code == "http_500"

    @pytest.mark.asyncio
    async def test_client_with_signer(self, config, http_client, discovery):
        """Test client with message signer."""
        signer = MockSigner()
        client = A2AClient(
            config=config,
            http_client=http_client,
            discovery=discovery,
            signer=signer,
        )

        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            200,
            {
                "message_id": "resp_123",
                "message_type": "ack",
                "sender_id": "agent_recipient",
                "recipient_id": "agent_sender",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "received",
                "payload": {},
            },
        )

        await client.send_message(
            recipient_url="https://recipient.example.com",
            message=A2AMessage(),
        )

        # Check that message was signed
        _, sent_data = http_client.post_calls[0]
        assert sent_data["signature"] is not None
        assert sent_data["signature"].startswith("mock_sig_")

    @pytest.mark.asyncio
    async def test_error_response_handling(self, client, http_client):
        """Test handling error type response."""
        http_client.add_post_response(
            "https://recipient.example.com/api/v2/a2a/messages",
            200,
            {
                "message_id": "resp_123",
                "message_type": "error",
                "sender_id": "agent_recipient",
                "recipient_id": "agent_sender",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "error": "Rate limit exceeded",
                "error_code": "rate_limited",
                "payload": {},
            },
        )

        response = await client.send_payment_request(
            recipient_url="https://recipient.example.com",
            amount_minor=5000,
            token="USDC",
            chain="base",
            destination="0x1234567890abcdef1234567890abcdef12345678",
        )

        assert response.success is False
        assert response.error == "Rate limit exceeded"
        assert response.error_code == "rate_limited"
