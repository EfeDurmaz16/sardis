"""Tests for EIP-712 typed data signing in external wallet checkout connect flow.

Covers:
- Valid EIP-712 signature verifies and connects wallet
- Session ID mismatch in signed data is rejected
- Chain ID mismatch in signed data is rejected
- Wrong wallet address (recovered != claimed) is rejected
- Backward-compatible EIP-191 still works with deprecation warning
- connect-params endpoint returns proper typed data structure
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data
from sardis_api.services.eip712_checkout import (
    EIP712_DOMAIN_NAME,
    EIP712_DOMAIN_VERSION,
    build_connect_typed_data,
    generate_nonce,
    verify_eip712_connect_signature,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

# Test account (deterministic for reproducibility)
TEST_PRIVATE_KEY = "0x" + "ab" * 32
TEST_ACCOUNT = Account.from_key(TEST_PRIVATE_KEY)
TEST_ADDRESS = TEST_ACCOUNT.address

# Another account (for wrong-signer tests)
WRONG_PRIVATE_KEY = "0x" + "cd" * 32
WRONG_ACCOUNT = Account.from_key(WRONG_PRIVATE_KEY)
WRONG_ADDRESS = WRONG_ACCOUNT.address

TEST_SESSION_ID = "sess_test_eip712_001"
TEST_CHAIN_ID = 8453  # Base mainnet
TEST_CLIENT_SECRET = "cs_abc123def456"


@dataclass
class FakeSession:
    session_id: str = TEST_SESSION_ID
    client_secret: str = TEST_CLIENT_SECRET
    merchant_id: str = "merch_001"
    amount: Decimal = Decimal("25.00")
    currency: str = "USDC"
    description: str = "Test checkout"
    status: str = "pending"
    payment_method: str | None = None
    tx_hash: str | None = None
    payer_wallet_id: str | None = None
    payer_wallet_address: str | None = None
    platform_fee_amount: Decimal | None = None
    net_amount: Decimal | None = None
    embed_origin: str | None = None
    expires_at: datetime | None = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(hours=1)
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )


def _sign_eip712(
    private_key: str,
    session_id: str,
    wallet_address: str,
    chain_id: int,
    nonce: str,
) -> str:
    """Sign EIP-712 typed data and return the hex signature."""
    typed_data = build_connect_typed_data(
        session_id=session_id,
        wallet_address=wallet_address,
        chain_id=chain_id,
        nonce=nonce,
    )
    signable = encode_typed_data(full_message=typed_data)
    signed = Account.from_key(private_key).sign_message(signable)
    return signed.signature.hex()


def _sign_eip191(private_key: str, message: str) -> str:
    """Sign an EIP-191 message and return the hex signature."""
    msg = encode_defunct(text=message)
    signed = Account.from_key(private_key).sign_message(msg)
    return signed.signature.hex()


# ---------------------------------------------------------------------------
# Unit tests for eip712_checkout service
# ---------------------------------------------------------------------------


class TestBuildConnectTypedData:
    """Tests for the typed data builder."""

    def test_structure_matches_eip712_spec(self):
        nonce = generate_nonce()
        td = build_connect_typed_data(
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=TEST_CHAIN_ID,
            nonce=nonce,
        )
        assert td["primaryType"] == "SardisCheckoutConnect"
        assert "EIP712Domain" in td["types"]
        assert "SardisCheckoutConnect" in td["types"]
        assert td["domain"]["name"] == EIP712_DOMAIN_NAME
        assert td["domain"]["version"] == EIP712_DOMAIN_VERSION
        assert td["domain"]["chainId"] == TEST_CHAIN_ID
        assert td["message"]["sessionId"] == TEST_SESSION_ID
        assert td["message"]["walletAddress"] == TEST_ADDRESS
        assert td["message"]["chainId"] == TEST_CHAIN_ID
        assert td["message"]["nonce"] == nonce

    def test_auto_generates_nonce(self):
        td1 = build_connect_typed_data(
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=TEST_CHAIN_ID,
        )
        td2 = build_connect_typed_data(
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=TEST_CHAIN_ID,
        )
        # Two calls should produce different nonces
        assert td1["message"]["nonce"] != td2["message"]["nonce"]

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_default_chain_id_from_env(self):
        td = build_connect_typed_data(
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
        )
        assert td["domain"]["chainId"] == 8453
        assert td["message"]["chainId"] == 8453

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base_sepolia"})
    def test_testnet_chain_id_from_env(self):
        td = build_connect_typed_data(
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
        )
        assert td["domain"]["chainId"] == 84532


class TestVerifyEip712ConnectSignature:
    """Tests for signature verification."""

    def test_valid_signature_verifies(self):
        nonce = generate_nonce()
        sig = _sign_eip712(
            TEST_PRIVATE_KEY, TEST_SESSION_ID, TEST_ADDRESS, TEST_CHAIN_ID, nonce
        )
        is_valid, error = verify_eip712_connect_signature(
            signature=sig,
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=TEST_CHAIN_ID,
            nonce=nonce,
        )
        assert is_valid is True
        assert error is None

    def test_wrong_session_id_fails(self):
        nonce = generate_nonce()
        # Sign with one session ID
        sig = _sign_eip712(
            TEST_PRIVATE_KEY, "sess_wrong_id", TEST_ADDRESS, TEST_CHAIN_ID, nonce
        )
        # Verify against a different session ID
        is_valid, error = verify_eip712_connect_signature(
            signature=sig,
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=TEST_CHAIN_ID,
            nonce=nonce,
        )
        assert is_valid is False
        assert error is not None
        assert "does not match" in error

    def test_wrong_chain_id_fails(self):
        nonce = generate_nonce()
        # Sign for Base mainnet
        sig = _sign_eip712(
            TEST_PRIVATE_KEY, TEST_SESSION_ID, TEST_ADDRESS, 8453, nonce
        )
        # Verify against a different chain ID
        is_valid, error = verify_eip712_connect_signature(
            signature=sig,
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=84532,  # Base Sepolia instead
            nonce=nonce,
        )
        assert is_valid is False
        assert error is not None
        assert "does not match" in error

    def test_wrong_wallet_address_fails(self):
        nonce = generate_nonce()
        # Sign with WRONG_ACCOUNT's key
        sig = _sign_eip712(
            WRONG_PRIVATE_KEY, TEST_SESSION_ID, TEST_ADDRESS, TEST_CHAIN_ID, nonce
        )
        # Verify: recovered address will be WRONG_ADDRESS, not TEST_ADDRESS
        is_valid, error = verify_eip712_connect_signature(
            signature=sig,
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=TEST_CHAIN_ID,
            nonce=nonce,
        )
        assert is_valid is False
        assert error is not None
        assert "does not match" in error

    def test_garbage_signature_fails(self):
        nonce = generate_nonce()
        is_valid, error = verify_eip712_connect_signature(
            signature="0x" + "00" * 65,
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=TEST_CHAIN_ID,
            nonce=nonce,
        )
        assert is_valid is False
        assert error is not None

    def test_wrong_nonce_fails(self):
        nonce = generate_nonce()
        sig = _sign_eip712(
            TEST_PRIVATE_KEY, TEST_SESSION_ID, TEST_ADDRESS, TEST_CHAIN_ID, nonce
        )
        # Verify with a different nonce
        is_valid, error = verify_eip712_connect_signature(
            signature=sig,
            session_id=TEST_SESSION_ID,
            wallet_address=TEST_ADDRESS,
            chain_id=TEST_CHAIN_ID,
            nonce="different_nonce",
        )
        assert is_valid is False
        assert error is not None


# ---------------------------------------------------------------------------
# Integration tests for API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_deps():
    """Create mock MerchantCheckoutDependencies."""
    from sardis_api.routers.merchant_checkout import MerchantCheckoutDependencies

    mock_repo = AsyncMock()
    mock_repo.get_session_by_secret = AsyncMock(return_value=FakeSession())
    mock_repo.update_session = AsyncMock()
    mock_connector = AsyncMock()

    return MerchantCheckoutDependencies(
        merchant_repo=mock_repo,
        sardis_connector=mock_connector,
    )


@pytest.fixture
def app(mock_deps):
    """Create a test FastAPI app with the public checkout router."""
    from fastapi import FastAPI
    from sardis_api.routers.merchant_checkout import get_deps, public_router

    test_app = FastAPI()
    test_app.include_router(public_router, prefix="/checkout")
    test_app.dependency_overrides[get_deps] = lambda: mock_deps
    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestConnectExternalEIP712:
    """Integration tests for the connect-external endpoint with EIP-712."""

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_valid_eip712_connects(self, client, mock_deps):
        """Valid EIP-712 signature successfully connects the wallet."""
        nonce = generate_nonce()
        sig = _sign_eip712(
            TEST_PRIVATE_KEY, TEST_SESSION_ID, TEST_ADDRESS, TEST_CHAIN_ID, nonce
        )

        resp = client.post(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-external",
            json={
                "address": TEST_ADDRESS,
                "signature": sig,
                "session_id": TEST_SESSION_ID,
                "chain_id": TEST_CHAIN_ID,
                "nonce": nonce,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "connected"
        assert data["address"] == TEST_ADDRESS
        assert data["session_id"] == TEST_SESSION_ID

        # Verify update_session was called with correct args
        mock_deps.merchant_repo.update_session.assert_called_once_with(
            TEST_SESSION_ID,
            payer_wallet_address=TEST_ADDRESS,
            payment_method="external_wallet",
        )

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_session_id_mismatch_rejected(self, client, mock_deps):
        """EIP-712 signature with wrong session_id is rejected."""
        nonce = generate_nonce()
        wrong_session = "sess_wrong_session"
        sig = _sign_eip712(
            TEST_PRIVATE_KEY, wrong_session, TEST_ADDRESS, TEST_CHAIN_ID, nonce
        )

        resp = client.post(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-external",
            json={
                "address": TEST_ADDRESS,
                "signature": sig,
                "session_id": wrong_session,  # Does not match FakeSession.session_id
                "chain_id": TEST_CHAIN_ID,
                "nonce": nonce,
            },
        )
        assert resp.status_code == 400
        assert "session ID" in resp.json()["detail"].lower() or "session" in resp.json()["detail"].lower()

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_chain_id_mismatch_rejected(self, client, mock_deps):
        """EIP-712 signature with wrong chain_id is rejected."""
        nonce = generate_nonce()
        wrong_chain = 84532  # Base Sepolia instead of Base mainnet
        sig = _sign_eip712(
            TEST_PRIVATE_KEY, TEST_SESSION_ID, TEST_ADDRESS, wrong_chain, nonce
        )

        resp = client.post(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-external",
            json={
                "address": TEST_ADDRESS,
                "signature": sig,
                "session_id": TEST_SESSION_ID,
                "chain_id": wrong_chain,
                "nonce": nonce,
            },
        )
        assert resp.status_code == 400
        assert "chain" in resp.json()["detail"].lower()

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_wrong_address_rejected(self, client, mock_deps):
        """EIP-712 signature from a different wallet is rejected."""
        nonce = generate_nonce()
        # Sign with WRONG key but claim TEST_ADDRESS
        sig = _sign_eip712(
            WRONG_PRIVATE_KEY, TEST_SESSION_ID, TEST_ADDRESS, TEST_CHAIN_ID, nonce
        )

        resp = client.post(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-external",
            json={
                "address": TEST_ADDRESS,
                "signature": sig,
                "session_id": TEST_SESSION_ID,
                "chain_id": TEST_CHAIN_ID,
                "nonce": nonce,
            },
        )
        assert resp.status_code == 400
        assert "does not match" in resp.json()["detail"].lower() or "signature" in resp.json()["detail"].lower()

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_eip191_backward_compatible(self, client, mock_deps):
        """Legacy EIP-191 signature still works (with deprecation warning)."""
        cs_prefix = TEST_CLIENT_SECRET[:8]
        message = f"Connect wallet to Sardis Checkout ({cs_prefix})"
        sig = _sign_eip191(TEST_PRIVATE_KEY, message)

        with patch("sardis_api.routers.merchant_checkout.logger") as mock_logger:
            resp = client.post(
                f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-external",
                json={
                    "address": TEST_ADDRESS,
                    "signature": sig,
                    "message": message,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "connected"

            # Check that deprecation warning was logged
            mock_logger.warning.assert_called()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "DEPRECATION" in warning_msg

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_eip191_bad_signature_rejected(self, client, mock_deps):
        """Legacy EIP-191 with wrong signer is rejected."""
        cs_prefix = TEST_CLIENT_SECRET[:8]
        message = f"Connect wallet to Sardis Checkout ({cs_prefix})"
        sig = _sign_eip191(WRONG_PRIVATE_KEY, message)

        resp = client.post(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-external",
            json={
                "address": TEST_ADDRESS,
                "signature": sig,
                "message": message,
            },
        )
        assert resp.status_code == 400

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_no_message_no_eip712_fields_rejected(self, client, mock_deps):
        """Request with neither EIP-712 fields nor EIP-191 message is rejected."""
        resp = client.post(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-external",
            json={
                "address": TEST_ADDRESS,
                "signature": "0x" + "ab" * 65,
                # No message, no session_id/chain_id/nonce
            },
        )
        assert resp.status_code == 400
        assert "EIP-712" in resp.json()["detail"] or "EIP-191" in resp.json()["detail"]


class TestConnectParams:
    """Integration tests for the connect-params endpoint."""

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_returns_typed_data(self, client, mock_deps):
        """connect-params returns a valid EIP-712 typed data structure."""
        resp = client.get(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-params",
            params={"address": TEST_ADDRESS},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "typed_data" in data
        assert "chain_id" in data
        assert "nonce" in data
        assert "session_id" in data

        td = data["typed_data"]
        assert td["primaryType"] == "SardisCheckoutConnect"
        assert td["domain"]["name"] == "Sardis Checkout"
        assert td["domain"]["version"] == "1"
        assert td["domain"]["chainId"] == 8453
        assert td["message"]["sessionId"] == TEST_SESSION_ID
        assert td["message"]["walletAddress"] == TEST_ADDRESS
        assert td["message"]["chainId"] == 8453
        assert data["chain_id"] == 8453

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_params_can_be_signed_and_verified(self, client, mock_deps):
        """Typed data from connect-params can be signed and used with connect-external."""
        # Step 1: Get connect params
        resp = client.get(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-params",
            params={"address": TEST_ADDRESS},
        )
        assert resp.status_code == 200
        params = resp.json()

        # Step 2: Sign the typed data
        signable = encode_typed_data(full_message=params["typed_data"])
        signed = TEST_ACCOUNT.sign_message(signable)

        # Step 3: Submit to connect-external
        resp = client.post(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-external",
            json={
                "address": TEST_ADDRESS,
                "signature": signed.signature.hex(),
                "session_id": params["session_id"],
                "chain_id": params["chain_id"],
                "nonce": params["nonce"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "connected"

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_expired_session_rejected(self, client, mock_deps):
        """connect-params rejects expired sessions."""
        expired = FakeSession(
            expires_at=datetime.now(UTC) - timedelta(hours=1)
        )
        mock_deps.merchant_repo.get_session_by_secret = AsyncMock(return_value=expired)

        resp = client.get(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-params",
            params={"address": TEST_ADDRESS},
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    @patch.dict("os.environ", {"SARDIS_CHECKOUT_CHAIN": "base"})
    def test_non_pending_session_rejected(self, client, mock_deps):
        """connect-params rejects non-pending sessions."""
        paid = FakeSession(status="paid")
        mock_deps.merchant_repo.get_session_by_secret = AsyncMock(return_value=paid)

        resp = client.get(
            f"/checkout/sessions/client/{TEST_CLIENT_SECRET}/connect-params",
            params={"address": TEST_ADDRESS},
        )
        assert resp.status_code == 400
