"""
Tests for compliance factory production guards.

Verifies that all compliance factory functions raise RuntimeError when
API keys are missing in production/staging environments, and allow mock
fallback only in dev/test/local environments.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROD_ENVS = ("prod", "production", "staging")
DEV_ENVS = ("dev", "test", "local", "")


# ---------------------------------------------------------------------------
# sanctions.py — create_sanctions_service
# ---------------------------------------------------------------------------

class TestSanctionsProductionGuard:
    """create_sanctions_service must refuse mock in prod/staging."""

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_raises_in_production_without_api_keys(self, env: str) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env}, clear=False):
            from sardis_compliance.sanctions import create_sanctions_service

            with pytest.raises(RuntimeError, match="sanctions"):
                create_sanctions_service()

    @pytest.mark.parametrize("env", DEV_ENVS)
    def test_allows_mock_in_dev(self, env: str) -> None:
        env_dict = {"SARDIS_ENVIRONMENT": env} if env else {}
        with patch.dict(os.environ, env_dict, clear=False):
            # Remove any env vars that would trigger a real provider
            for key in (
                "SARDIS_COMPLIANCE_SCREENING_PROVIDER",
                "ELLIPTIC_API_KEY",
                "ELLIPTIC_API_SECRET",
                "CIRCLE_API_KEY",
            ):
                os.environ.pop(key, None)

            from sardis_compliance.sanctions import create_sanctions_service

            svc = create_sanctions_service()
            assert svc is not None

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_circle_raises_in_production_without_key(self, env: str) -> None:
        with patch.dict(
            os.environ,
            {"SARDIS_ENVIRONMENT": env, "SARDIS_COMPLIANCE_SCREENING_PROVIDER": "circle"},
            clear=False,
        ):
            os.environ.pop("CIRCLE_API_KEY", None)

            from sardis_compliance.sanctions import create_sanctions_service

            with pytest.raises(RuntimeError, match="CIRCLE_API_KEY"):
                create_sanctions_service(provider_name="circle")

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_elliptic_raises_in_production_without_key(self, env: str) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env}, clear=False):
            from sardis_compliance.sanctions import create_sanctions_service

            with pytest.raises(RuntimeError, match="Elliptic"):
                create_sanctions_service(provider_name="elliptic")


# ---------------------------------------------------------------------------
# kyc.py — create_kyc_service
# ---------------------------------------------------------------------------

class TestKYCProductionGuard:
    """create_kyc_service must refuse mock in prod/staging."""

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_raises_in_production_without_api_key(self, env: str) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env}, clear=False):
            from sardis_compliance.kyc import create_kyc_service

            with pytest.raises(RuntimeError, match="Persona KYC"):
                create_kyc_service()

    @pytest.mark.parametrize("env", DEV_ENVS)
    def test_allows_mock_in_dev(self, env: str) -> None:
        env_dict = {"SARDIS_ENVIRONMENT": env} if env else {}
        with patch.dict(os.environ, env_dict, clear=False):
            from sardis_compliance.kyc import create_kyc_service

            svc = create_kyc_service()
            assert svc is not None


# ---------------------------------------------------------------------------
# kyb.py — create_kyb_service
# ---------------------------------------------------------------------------

class TestKYBProductionGuard:
    """create_kyb_service must refuse mock in prod/staging."""

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_raises_in_production_without_api_key(self, env: str) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env}, clear=False):
            from sardis_compliance.kyb import create_kyb_service

            with pytest.raises(RuntimeError, match="Persona KYB"):
                create_kyb_service()

    @pytest.mark.parametrize("env", DEV_ENVS)
    def test_allows_mock_in_dev(self, env: str) -> None:
        env_dict = {"SARDIS_ENVIRONMENT": env} if env else {}
        with patch.dict(os.environ, env_dict, clear=False):
            from sardis_compliance.kyb import create_kyb_service

            svc = create_kyb_service()
            assert svc is not None


# ---------------------------------------------------------------------------
# pep.py — create_pep_service
# ---------------------------------------------------------------------------

class TestPEPProductionGuard:
    """create_pep_service must refuse mock in prod/staging."""

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_raises_in_production_without_api_key(self, env: str) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env}, clear=False):
            from sardis_compliance.pep import create_pep_service

            with pytest.raises(RuntimeError, match="PEP"):
                create_pep_service()

    @pytest.mark.parametrize("env", DEV_ENVS)
    def test_allows_mock_in_dev(self, env: str) -> None:
        env_dict = {"SARDIS_ENVIRONMENT": env} if env else {}
        with patch.dict(os.environ, env_dict, clear=False):
            from sardis_compliance.pep import create_pep_service

            svc = create_pep_service()
            assert svc is not None

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_unknown_provider_raises_in_production(self, env: str) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env}, clear=False):
            from sardis_compliance.pep import create_pep_service

            with pytest.raises(RuntimeError, match="Unknown PEP provider"):
                create_pep_service(api_key="fake-key", provider_name="nonexistent")


# ---------------------------------------------------------------------------
# adverse_media.py — create_adverse_media_service
# ---------------------------------------------------------------------------

class TestAdverseMediaProductionGuard:
    """create_adverse_media_service must refuse mock in prod/staging."""

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_raises_in_production_without_api_key(self, env: str) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env}, clear=False):
            from sardis_compliance.adverse_media import create_adverse_media_service

            with pytest.raises(RuntimeError, match="Adverse media"):
                create_adverse_media_service()

    @pytest.mark.parametrize("env", DEV_ENVS)
    def test_allows_mock_in_dev(self, env: str) -> None:
        env_dict = {"SARDIS_ENVIRONMENT": env} if env else {}
        with patch.dict(os.environ, env_dict, clear=False):
            from sardis_compliance.adverse_media import create_adverse_media_service

            svc = create_adverse_media_service()
            assert svc is not None

    @pytest.mark.parametrize("env", PROD_ENVS)
    def test_unknown_provider_raises_in_production(self, env: str) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": env}, clear=False):
            from sardis_compliance.adverse_media import create_adverse_media_service

            with pytest.raises(RuntimeError, match="Unknown adverse media provider"):
                create_adverse_media_service(
                    api_key="fake-key",
                    account_id="fake-account",
                    provider_name="nonexistent",
                )


# ---------------------------------------------------------------------------
# Cross-cutting: staging environment specifically
# ---------------------------------------------------------------------------

class TestStagingBlocksMock:
    """Staging must be treated the same as production."""

    def test_sanctions_staging(self) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "staging"}, clear=False):
            for key in (
                "SARDIS_COMPLIANCE_SCREENING_PROVIDER",
                "ELLIPTIC_API_KEY",
                "ELLIPTIC_API_SECRET",
                "CIRCLE_API_KEY",
            ):
                os.environ.pop(key, None)

            from sardis_compliance.sanctions import create_sanctions_service

            with pytest.raises(RuntimeError):
                create_sanctions_service()

    def test_kyc_staging(self) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "staging"}, clear=False):
            from sardis_compliance.kyc import create_kyc_service

            with pytest.raises(RuntimeError):
                create_kyc_service()

    def test_kyb_staging(self) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "staging"}, clear=False):
            from sardis_compliance.kyb import create_kyb_service

            with pytest.raises(RuntimeError):
                create_kyb_service()

    def test_pep_staging(self) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "staging"}, clear=False):
            from sardis_compliance.pep import create_pep_service

            with pytest.raises(RuntimeError):
                create_pep_service()

    def test_adverse_media_staging(self) -> None:
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "staging"}, clear=False):
            from sardis_compliance.adverse_media import create_adverse_media_service

            with pytest.raises(RuntimeError):
                create_adverse_media_service()
