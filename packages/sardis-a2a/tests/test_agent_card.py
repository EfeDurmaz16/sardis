"""Tests for A2A agent card."""

from datetime import datetime, timezone

import pytest

from sardis_a2a.agent_card import (
    AgentCapability,
    PaymentCapability,
    ServiceEndpoint,
    SardisAgentCard,
    create_sardis_agent_card,
)


class TestAgentCapability:
    """Tests for AgentCapability enum."""

    def test_payment_capabilities(self):
        """Test payment capability values."""
        assert AgentCapability.PAYMENT_EXECUTE.value == "payment.execute"
        assert AgentCapability.PAYMENT_VERIFY.value == "payment.verify"
        assert AgentCapability.PAYMENT_REFUND.value == "payment.refund"

    def test_mandate_capabilities(self):
        """Test mandate capability values."""
        assert AgentCapability.MANDATE_INGEST.value == "mandate.ingest"
        assert AgentCapability.MANDATE_SIGN.value == "mandate.sign"

    def test_wallet_capabilities(self):
        """Test wallet capability values."""
        assert AgentCapability.WALLET_BALANCE.value == "wallet.balance"
        assert AgentCapability.WALLET_HOLD.value == "wallet.hold"

    def test_checkout_capabilities(self):
        """Test checkout capability values."""
        assert AgentCapability.CHECKOUT_CREATE.value == "checkout.create"
        assert AgentCapability.CHECKOUT_COMPLETE.value == "checkout.complete"

    def test_micropay_capability(self):
        """Test micropay capability value."""
        assert AgentCapability.X402_MICROPAY.value == "x402.micropay"


class TestPaymentCapability:
    """Tests for PaymentCapability."""

    def test_default_values(self):
        """Test default payment capability values."""
        cap = PaymentCapability()

        assert "USDC" in cap.supported_tokens
        assert "USDT" in cap.supported_tokens
        assert "PYUSD" in cap.supported_tokens
        assert "EURC" in cap.supported_tokens

        assert "base" in cap.supported_chains
        assert "polygon" in cap.supported_chains
        assert "ethereum" in cap.supported_chains
        assert "arbitrum" in cap.supported_chains
        assert "optimism" in cap.supported_chains

        assert cap.min_amount_minor == 100  # $1.00
        assert cap.max_amount_minor == 100_000_00  # $100,000.00

        assert cap.ap2_compliant is True
        assert cap.x402_compliant is True
        assert cap.ucp_compliant is True

    def test_custom_values(self):
        """Test custom payment capability values."""
        cap = PaymentCapability(
            supported_tokens=["USDC"],
            supported_chains=["base", "polygon"],
            min_amount_minor=500,
            max_amount_minor=50_000_00,
            ap2_compliant=True,
            x402_compliant=False,
            ucp_compliant=True,
        )

        assert cap.supported_tokens == ["USDC"]
        assert cap.supported_chains == ["base", "polygon"]
        assert cap.min_amount_minor == 500
        assert cap.max_amount_minor == 50_000_00
        assert cap.x402_compliant is False

    def test_to_dict(self):
        """Test serialization to dictionary."""
        cap = PaymentCapability(
            supported_tokens=["USDC", "USDT"],
            supported_chains=["base"],
            min_amount_minor=100,
            max_amount_minor=10_000_00,
        )

        data = cap.to_dict()

        assert data["supported_tokens"] == ["USDC", "USDT"]
        assert data["supported_chains"] == ["base"]
        assert data["min_amount_minor"] == 100
        assert data["max_amount_minor"] == 10_000_00
        assert data["ap2_compliant"] is True


class TestServiceEndpoint:
    """Tests for ServiceEndpoint."""

    def test_create_endpoint(self):
        """Test creating a service endpoint."""
        endpoint = ServiceEndpoint(
            url="https://api.sardis.sh/v2",
            protocol="https",
            auth_required=True,
            auth_type="bearer",
        )

        assert endpoint.url == "https://api.sardis.sh/v2"
        assert endpoint.protocol == "https"
        assert endpoint.auth_required is True
        assert endpoint.auth_type == "bearer"

    def test_default_values(self):
        """Test default endpoint values."""
        endpoint = ServiceEndpoint(url="https://example.com")

        assert endpoint.protocol == "https"
        assert endpoint.auth_required is False
        assert endpoint.auth_type is None

    def test_to_dict(self):
        """Test endpoint serialization."""
        endpoint = ServiceEndpoint(
            url="https://api.sardis.sh/v2",
            protocol="https",
            auth_required=True,
            auth_type="api_key",
        )

        data = endpoint.to_dict()

        assert data["url"] == "https://api.sardis.sh/v2"
        assert data["protocol"] == "https"
        assert data["auth_required"] is True
        assert data["auth_type"] == "api_key"


class TestSardisAgentCard:
    """Tests for SardisAgentCard."""

    @pytest.fixture
    def agent_card(self):
        """Create a sample agent card."""
        return SardisAgentCard(
            agent_id="agent_123",
            agent_name="Test Agent",
            agent_version="1.0.0",
            agent_description="A test agent",
            operator_name="Test Operator",
            operator_url="https://test.com",
            capabilities=[
                AgentCapability.PAYMENT_EXECUTE,
                AgentCapability.PAYMENT_VERIFY,
                AgentCapability.CHECKOUT_CREATE,
            ],
        )

    def test_create_agent_card(self, agent_card):
        """Test creating an agent card."""
        assert agent_card.agent_id == "agent_123"
        assert agent_card.agent_name == "Test Agent"
        assert agent_card.agent_version == "1.0.0"
        assert agent_card.operator_name == "Test Operator"
        assert len(agent_card.capabilities) == 3

    def test_default_capabilities(self):
        """Test default agent card capabilities."""
        card = SardisAgentCard(
            agent_id="agent_1",
            agent_name="Agent",
        )

        # Check default capabilities include core functions
        assert AgentCapability.PAYMENT_EXECUTE in card.capabilities
        assert AgentCapability.PAYMENT_VERIFY in card.capabilities
        assert AgentCapability.CHECKOUT_CREATE in card.capabilities

    def test_supports_capability(self, agent_card):
        """Test capability checking."""
        assert agent_card.supports_capability(AgentCapability.PAYMENT_EXECUTE) is True
        assert agent_card.supports_capability(AgentCapability.PAYMENT_VERIFY) is True
        assert agent_card.supports_capability(AgentCapability.CHECKOUT_CREATE) is True
        assert agent_card.supports_capability(AgentCapability.PAYMENT_REFUND) is False

    def test_supports_token(self, agent_card):
        """Test token support checking."""
        # Default PaymentCapability includes USDC, USDT, etc.
        assert agent_card.supports_token("USDC") is True
        assert agent_card.supports_token("usdc") is True  # Case insensitive
        assert agent_card.supports_token("USDT") is True
        assert agent_card.supports_token("UNKNOWN") is False

    def test_supports_chain(self, agent_card):
        """Test chain support checking."""
        # Default PaymentCapability includes base, polygon, etc.
        assert agent_card.supports_chain("base") is True
        assert agent_card.supports_chain("BASE") is True  # Case insensitive
        assert agent_card.supports_chain("polygon") is True
        assert agent_card.supports_chain("unknown") is False

    def test_to_dict(self, agent_card):
        """Test agent card serialization."""
        data = agent_card.to_dict()

        assert data["agent_id"] == "agent_123"
        assert data["name"] == "Test Agent"
        assert data["version"] == "1.0.0"
        assert data["description"] == "A test agent"
        assert data["operator"]["name"] == "Test Operator"
        assert data["operator"]["url"] == "https://test.com"
        assert "payment.execute" in data["capabilities"]
        assert "payment" in data
        assert "endpoints" in data

    def test_to_dict_with_endpoints(self):
        """Test serialization with endpoints."""
        card = SardisAgentCard(
            agent_id="agent_123",
            agent_name="Test Agent",
            api_endpoint=ServiceEndpoint(
                url="https://api.test.com",
                auth_required=True,
                auth_type="bearer",
            ),
            mcp_endpoint="npx @sardis/mcp-server",
            a2a_endpoint=ServiceEndpoint(
                url="https://api.test.com/a2a",
                auth_required=True,
                auth_type="signature",
            ),
        )

        data = card.to_dict()

        assert "api" in data["endpoints"]
        assert data["endpoints"]["api"]["url"] == "https://api.test.com"
        assert data["endpoints"]["mcp"] == "npx @sardis/mcp-server"
        assert "a2a" in data["endpoints"]

    def test_to_dict_with_signing(self):
        """Test serialization with signing key."""
        card = SardisAgentCard(
            agent_id="agent_123",
            agent_name="Test Agent",
            signing_key_id="key_1",
            public_key="base64_encoded_key",
            key_algorithm="Ed25519",
        )

        data = card.to_dict()

        assert data["signing"] is not None
        assert data["signing"]["key_id"] == "key_1"
        assert data["signing"]["public_key"] == "base64_encoded_key"
        assert data["signing"]["algorithm"] == "Ed25519"

    def test_timestamps(self):
        """Test timestamp fields."""
        card = SardisAgentCard(
            agent_id="agent_1",
            agent_name="Agent",
        )

        assert isinstance(card.created_at, datetime)
        assert isinstance(card.updated_at, datetime)
        assert card.created_at.tzinfo == timezone.utc


class TestCreateSardisAgentCard:
    """Tests for create_sardis_agent_card helper."""

    def test_create_basic_card(self):
        """Test creating a basic agent card."""
        card = create_sardis_agent_card(
            agent_id="agent_test",
            agent_name="Test Agent",
            api_base_url="https://api.sardis.sh",
        )

        assert card.agent_id == "agent_test"
        assert card.agent_name == "Test Agent"
        assert card.agent_description == "Sardis Payment Agent - secure AI payment infrastructure"
        assert card.api_endpoint is not None
        assert card.api_endpoint.url == "https://api.sardis.sh/api/v2"
        assert card.api_endpoint.auth_required is True
        assert card.a2a_endpoint is not None
        assert card.a2a_endpoint.url == "https://api.sardis.sh/api/v2/a2a"

    def test_create_card_with_mcp(self):
        """Test creating card with MCP command."""
        card = create_sardis_agent_card(
            agent_id="agent_test",
            agent_name="Test Agent",
            api_base_url="https://api.sardis.sh",
            mcp_command="npx @sardis/mcp-server",
        )

        assert card.mcp_endpoint == "npx @sardis/mcp-server"

    def test_create_card_with_signing(self):
        """Test creating card with signing key."""
        card = create_sardis_agent_card(
            agent_id="agent_test",
            agent_name="Test Agent",
            api_base_url="https://api.sardis.sh",
            signing_key_id="key_123",
            public_key="base64_key",
        )

        assert card.signing_key_id == "key_123"
        assert card.public_key == "base64_key"
