"""Tests for Privado ID zero-knowledge identity provider.

Covers issue #138. All API calls are mocked.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from sardis_compliance.providers.privado_id import (
    CREDENTIAL_SCHEMAS,
    PRIVADO_API_URLS,
    AuthRequest,
    CredentialQuery,
    CredentialStatus,
    IssuedCredential,
    PrivadoIDError,
    PrivadoIDProvider,
    ProofVerificationResult,
    ProofVerificationStatus,
    QueryOperator,
    build_age_query,
    build_country_query,
    build_humanity_query,
)


# ============ Mock Responses ============

ISSUE_CREDENTIAL_RESPONSE = {
    "id": "cred_abc123",
    "issuer": "did:iden3:polygon:amoy:test_issuer",
}

VERIFY_PROOF_VALID_RESPONSE = {
    "verified": True,
    "revoked": False,
}

VERIFY_PROOF_INVALID_RESPONSE = {
    "verified": False,
    "revoked": False,
}

CREDENTIAL_STATUS_ACTIVE = {
    "id": "cred_abc123",
    "revoked": False,
}

CREDENTIAL_STATUS_REVOKED = {
    "id": "cred_abc123",
    "revoked": True,
}


def _mock_response(json_data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=json_data,
        request=httpx.Request("POST", "https://issuer-node.polygonid.me/v1/credentials"),
    )


# ============ Provider Init Tests ============

class TestProviderInit:
    def test_defaults(self):
        provider = PrivadoIDProvider(
            issuer_url="https://issuer.test",
            issuer_user="admin",
            issuer_password="secret",
        )
        assert provider.is_configured is True

    def test_not_configured_no_user(self):
        provider = PrivadoIDProvider(
            issuer_url="https://issuer.test",
            issuer_user="",
            issuer_password="secret",
        )
        assert provider.is_configured is False

    def test_not_configured_no_password(self):
        provider = PrivadoIDProvider(
            issuer_url="https://issuer.test",
            issuer_user="admin",
            issuer_password="",
        )
        assert provider.is_configured is False

    def test_env_var_config(self):
        with patch.dict("os.environ", {
            "PRIVADO_ID_ISSUER_URL": "https://custom.issuer",
            "PRIVADO_ID_ISSUER_USER": "env-user",
            "PRIVADO_ID_ISSUER_PASSWORD": "env-pass",
        }):
            provider = PrivadoIDProvider()
            assert provider.is_configured is True
            assert provider._issuer_url == "https://custom.issuer"

    def test_testnet_default(self):
        provider = PrivadoIDProvider(
            issuer_user="u", issuer_password="p",
        )
        assert "polygonid.me" in provider._issuer_url

    def test_mainnet_environment(self):
        provider = PrivadoIDProvider(
            issuer_user="u", issuer_password="p",
            environment="mainnet",
        )
        assert "privado.id" in provider._issuer_url


# ============ Credential Query Tests ============

class TestCredentialQuery:
    def test_basic_query(self):
        q = CredentialQuery(
            schema_url="https://example.com/schema.jsonld",
            credential_type="TestCredential",
            field_name="age",
            operator=QueryOperator.GREATER_THAN,
            value=[18],
        )
        d = q.to_dict()
        assert d["type"] == "TestCredential"
        assert d["context"] == "https://example.com/schema.jsonld"
        assert d["allowedIssuers"] == ["*"]
        assert d["credentialSubject"]["age"]["$operator"] == 3

    def test_query_with_list_values(self):
        q = CredentialQuery(
            schema_url="https://example.com/schema.jsonld",
            credential_type="CountryCredential",
            field_name="countryCode",
            operator=QueryOperator.IN,
            value=[840, 276, 826],
        )
        d = q.to_dict()
        assert d["credentialSubject"]["countryCode"]["$value"] == [840, 276, 826]

    def test_query_single_value(self):
        q = CredentialQuery(
            schema_url="https://example.com/schema.jsonld",
            credential_type="Test",
            field_name="isHuman",
            operator=QueryOperator.EQUALS,
            value=[1],
        )
        d = q.to_dict()
        assert d["credentialSubject"]["isHuman"]["$value"] == 1

    def test_query_no_value(self):
        q = CredentialQuery(
            schema_url="https://example.com/schema.jsonld",
            credential_type="Test",
            field_name="exists",
            operator=QueryOperator.EXISTS,
        )
        d = q.to_dict()
        assert "$value" not in d["credentialSubject"]["exists"]


# ============ Common Query Builder Tests ============

class TestQueryBuilders:
    def test_age_query(self):
        q = build_age_query(18)
        assert q.credential_type == "KYCAgeCredential"
        assert q.operator == QueryOperator.LESS_THAN
        assert len(q.value) == 1
        assert q.value[0] > 20000000  # YYYYMMDD format

    def test_age_query_custom(self):
        q = build_age_query(21)
        assert q.value[0] > 20000000

    def test_country_allowed(self):
        q = build_country_query(allowed_countries=[840, 276])
        assert q.operator == QueryOperator.IN
        assert q.value == [840, 276]

    def test_country_blocked(self):
        q = build_country_query(blocked_countries=[408, 364])
        assert q.operator == QueryOperator.NOT_IN
        assert q.value == [408, 364]

    def test_humanity_query(self):
        q = build_humanity_query()
        assert q.credential_type == "ProofOfHumanity"
        assert q.operator == QueryOperator.EQUALS
        assert q.value == [1]


# ============ Auth Request Tests ============

class TestAuthRequest:
    def test_create_auth_request(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        query = build_age_query(18)
        auth_req = provider.create_auth_request(query, reason="Verify age")
        assert isinstance(auth_req, AuthRequest)
        assert auth_req.request_id in provider._pending_requests
        assert auth_req.reason == "Verify age"

    def test_auth_request_to_dict(self):
        query = build_age_query(18)
        auth_req = AuthRequest(request_id="test123", query=query, reason="Test")
        d = auth_req.to_dict()
        assert d["id"] == "test123"
        assert d["type"] == "https://iden3-communication.io/authorization/1.0/request"
        assert len(d["body"]["scope"]) >= 1
        assert d["body"]["scope"][0]["circuitId"] == "credentialAtomicQueryV3"

    def test_custom_request_id(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        query = build_age_query(18)
        auth_req = provider.create_auth_request(query, request_id="custom_id")
        assert auth_req.request_id == "custom_id"


# ============ Credential Issuance Tests ============

class TestIssueCredential:
    @pytest.mark.asyncio
    async def test_issue_credential(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        mock_resp = _mock_response(ISSUE_CREDENTIAL_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            cred = await provider.issue_credential(
                holder_did="did:iden3:polygon:amoy:holder123",
                credential_type="KYCAgeCredential",
                schema_url=CREDENTIAL_SCHEMAS["kyc_age"],
                claims={"birthday": 19900115},
            )

        assert isinstance(cred, IssuedCredential)
        assert cred.credential_id == "cred_abc123"
        assert cred.credential_type == "KYCAgeCredential"
        assert cred.status == CredentialStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_issue_not_configured(self):
        provider = PrivadoIDProvider(issuer_user="", issuer_password="")
        with pytest.raises(PrivadoIDError, match="not configured"):
            await provider.issue_credential(
                holder_did="did:test",
                credential_type="Test",
                schema_url="https://test",
                claims={},
            )

    @pytest.mark.asyncio
    async def test_issue_api_error(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        error_resp = httpx.Response(
            status_code=500,
            json={"error": "Server error"},
            request=httpx.Request("POST", "https://test/v1/credentials"),
        )
        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "Error", request=error_resp.request, response=error_resp,
            ),
        ):
            with pytest.raises(PrivadoIDError, match="500"):
                await provider.issue_credential(
                    holder_did="did:test",
                    credential_type="Test",
                    schema_url="https://test",
                    claims={},
                )


# ============ Proof Verification Tests ============

class TestVerifyProof:
    @pytest.mark.asyncio
    async def test_valid_proof(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        proof_data = {
            "body": {
                "scope": [{
                    "type": "KYCAgeCredential",
                    "issuer": "did:iden3:test_issuer",
                }]
            }
        }
        mock_resp = _mock_response(VERIFY_PROOF_VALID_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.verify_proof(proof_data)

        assert isinstance(result, ProofVerificationResult)
        assert result.is_valid is True
        assert result.status == ProofVerificationStatus.VALID
        assert result.proof_valid is True
        assert result.credential_revoked is False

    @pytest.mark.asyncio
    async def test_invalid_proof(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        proof_data = {"body": {"scope": [{"type": "Test"}]}}
        mock_resp = _mock_response(VERIFY_PROOF_INVALID_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.verify_proof(proof_data)

        assert result.is_valid is False
        assert result.status == ProofVerificationStatus.INVALID

    @pytest.mark.asyncio
    async def test_empty_scope(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        result = await provider.verify_proof({"body": {"scope": []}})
        assert result.status == ProofVerificationStatus.INVALID

    @pytest.mark.asyncio
    async def test_verify_not_configured(self):
        provider = PrivadoIDProvider(issuer_user="", issuer_password="")
        with pytest.raises(PrivadoIDError, match="not configured"):
            await provider.verify_proof({"body": {"scope": [{"type": "T"}]}})

    @pytest.mark.asyncio
    async def test_verify_cleans_pending(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        query = build_age_query(18)
        auth_req = provider.create_auth_request(query, request_id="req_1")
        assert "req_1" in provider._pending_requests

        proof_data = {"body": {"scope": [{"type": "Test"}]}}
        mock_resp = _mock_response(VERIFY_PROOF_VALID_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            await provider.verify_proof(proof_data, request_id="req_1")

        assert "req_1" not in provider._pending_requests


# ============ Credential Status Tests ============

class TestCredentialStatus:
    @pytest.mark.asyncio
    async def test_active_credential(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        mock_resp = _mock_response(CREDENTIAL_STATUS_ACTIVE)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            status = await provider.check_credential_status("cred_abc123")

        assert status == CredentialStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_revoked_credential(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        mock_resp = _mock_response(CREDENTIAL_STATUS_REVOKED)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            status = await provider.check_credential_status("cred_abc123")

        assert status == CredentialStatus.REVOKED


# ============ Revoke Credential Tests ============

class TestRevokeCredential:
    @pytest.mark.asyncio
    async def test_revoke_success(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        mock_resp = _mock_response({"message": "revoked"})

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.revoke_credential("cred_abc123", nonce=42)

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_not_configured(self):
        provider = PrivadoIDProvider(issuer_user="", issuer_password="")
        with pytest.raises(PrivadoIDError, match="not configured"):
            await provider.revoke_credential("cred_abc123")


# ============ Health Check Tests ============

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        mock_resp = httpx.Response(
            200, json={"status": "ok"},
            request=httpx.Request("GET", "https://test/status"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_unreachable(self):
        provider = PrivadoIDProvider(
            issuer_url="https://test", issuer_user="u", issuer_password="p",
        )
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("refused"),
        ):
            assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_not_configured(self):
        provider = PrivadoIDProvider(issuer_user="", issuer_password="")
        assert await provider.health_check() is False


# ============ ProofVerificationResult Properties ============

class TestProofVerificationResult:
    def test_is_valid_true(self):
        result = ProofVerificationResult(
            status=ProofVerificationStatus.VALID,
            proof_valid=True,
            credential_revoked=False,
        )
        assert result.is_valid is True

    def test_is_valid_revoked(self):
        result = ProofVerificationResult(
            status=ProofVerificationStatus.VALID,
            proof_valid=True,
            credential_revoked=True,
        )
        assert result.is_valid is False

    def test_is_valid_invalid_status(self):
        result = ProofVerificationResult(
            status=ProofVerificationStatus.INVALID,
            proof_valid=False,
        )
        assert result.is_valid is False


# ============ Query Operator Tests ============

class TestQueryOperator:
    def test_all_operators(self):
        assert QueryOperator.EQUALS.value == 1
        assert QueryOperator.LESS_THAN.value == 2
        assert QueryOperator.GREATER_THAN.value == 3
        assert QueryOperator.IN.value == 4
        assert QueryOperator.NOT_IN.value == 5
        assert QueryOperator.SD.value == 16


# ============ Module Export Tests ============

class TestModuleExports:
    def test_from_providers(self):
        from sardis_compliance.providers.privado_id import (
            PrivadoIDProvider,
            build_age_query,
            build_country_query,
            build_humanity_query,
        )
        assert all([PrivadoIDProvider, build_age_query, build_country_query, build_humanity_query])
