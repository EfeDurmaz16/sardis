"""Tests for MiCA (Markets in Crypto-Assets Regulation) compliance.

Covers issue #141. Tests CASP authorization, stablecoin classification,
transaction assessment, SAR deadlines, risk disclosures, whitepaper
validation, and jurisdiction checks.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from sardis_compliance.mica import (
    EU_EEA_COUNTRIES,
    SAR_DEADLINES,
    SIGNIFICANT_EMT_RESERVE_EUR,
    STABLECOIN_CLASSIFICATION,
    TRAVEL_RULE_THRESHOLD_EUR,
    CASPAuthorization,
    CASPService,
    CryptoAssetClass,
    DisclosureType,
    MiCAComplianceEngine,
    MiCASARReport,
    MiCAStatus,
    RiskDisclosure,
    SARRegion,
    StablecoinAssessment,
    TransactionAssessment,
    TransactionRisk,
    WhitepaperField,
    WhitepaperValidation,
    classify_stablecoin,
    create_mica_engine,
    get_sar_deadline,
    is_eu_country,
)


# ============ Token Classification Tests ============


class TestTokenClassification:
    def test_usdc_is_emt(self):
        engine = MiCAComplianceEngine()
        assert engine.classify_token("USDC") == CryptoAssetClass.E_MONEY_TOKEN

    def test_eurc_is_emt(self):
        engine = MiCAComplianceEngine()
        assert engine.classify_token("EURC") == CryptoAssetClass.E_MONEY_TOKEN

    def test_dai_is_art(self):
        engine = MiCAComplianceEngine()
        assert engine.classify_token("DAI") == CryptoAssetClass.ASSET_REFERENCED_TOKEN

    def test_btc_is_other(self):
        engine = MiCAComplianceEngine()
        assert engine.classify_token("BTC") == CryptoAssetClass.OTHER_CRYPTO_ASSET

    def test_unknown_token(self):
        engine = MiCAComplianceEngine()
        assert engine.classify_token("UNKNOWN") == CryptoAssetClass.OTHER_CRYPTO_ASSET

    def test_case_insensitive(self):
        engine = MiCAComplianceEngine()
        assert engine.classify_token("usdc") == CryptoAssetClass.E_MONEY_TOKEN

    def test_classify_stablecoin_helper(self):
        assert classify_stablecoin("USDT") == CryptoAssetClass.E_MONEY_TOKEN
        assert classify_stablecoin("ETH") == CryptoAssetClass.OTHER_CRYPTO_ASSET


# ============ Stablecoin Assessment Tests ============


class TestStablecoinAssessment:
    def test_basic_assessment(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin("USDC", issuer_name="Circle")
        assert isinstance(result, StablecoinAssessment)
        assert result.token_symbol == "USDC"
        assert result.asset_class == CryptoAssetClass.E_MONEY_TOKEN
        assert result.issuer_name == "Circle"

    def test_significant_by_reserve(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin(
            "USDC",
            reserve_amount_eur=Decimal("6000000000"),  # 6B EUR
        )
        assert result.is_significant is True

    def test_significant_by_volume(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin(
            "USDC",
            daily_tx_volume=3_000_000,
        )
        assert result.is_significant is True

    def test_significant_by_value(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin(
            "USDC",
            daily_tx_value_eur=Decimal("600000000"),
        )
        assert result.is_significant is True

    def test_not_significant(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin(
            "USDC",
            reserve_amount_eur=Decimal("100000"),
        )
        assert result.is_significant is False

    def test_other_token_not_significant(self):
        """Non-stablecoins can't be significant EMT/ART."""
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin(
            "BTC",
            reserve_amount_eur=Decimal("999999999999"),
        )
        assert result.is_significant is False

    def test_eba_supervision(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin(
            "USDC",
            reserve_amount_eur=Decimal("6000000000"),
        )
        assert result.requires_eba_supervision is True

    def test_compliance_score_full(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin(
            "USDC",
            has_whitepaper=True,
            issuer_authorized=True,
            reserve_compliant=True,
            redemption_rights=True,
        )
        assert result.compliance_score == 100

    def test_compliance_score_partial(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin(
            "USDC",
            has_whitepaper=True,
            issuer_authorized=False,
            reserve_compliant=True,
            redemption_rights=False,
        )
        assert result.compliance_score == 50

    def test_compliance_score_zero(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_stablecoin("USDC")
        assert result.compliance_score == 0


# ============ Transaction Assessment Tests ============


class TestTransactionAssessment:
    def test_low_value_eu_internal(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx1", amount_eur=Decimal("500"),
            source_country="DE", destination_country="FR", token="USDC",
        )
        assert result.risk == TransactionRisk.LOW
        assert result.requires_travel_rule is False
        assert result.is_eu_transaction is True

    def test_travel_rule_threshold(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx2", amount_eur=Decimal("1000"),
            source_country="DE", destination_country="FR", token="USDC",
        )
        assert result.requires_travel_rule is True

    def test_travel_rule_below_threshold(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx3", amount_eur=Decimal("999.99"),
            source_country="DE", destination_country="FR", token="USDC",
        )
        assert result.requires_travel_rule is False

    def test_cross_border_eu_non_eu(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx4", amount_eur=Decimal("5000"),
            source_country="DE", destination_country="US", token="USDC",
        )
        assert result.risk == TransactionRisk.MEDIUM
        assert "cross_border_eu_non_eu" in result.flags
        assert result.requires_enhanced_monitoring is True

    def test_high_value_transaction(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx5", amount_eur=Decimal("20000"),
            source_country="DE", destination_country="DE", token="USDC",
        )
        assert result.risk == TransactionRisk.HIGH
        assert "high_value_above_15k_eur" in result.flags

    def test_non_eu_transaction(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx6", amount_eur=Decimal("5000"),
            source_country="US", destination_country="JP", token="USDC",
        )
        assert "non_eu_transaction" in result.flags

    def test_stablecoin_disclosure(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx7", amount_eur=Decimal("500"),
            source_country="DE", destination_country="FR", token="USDC",
        )
        assert DisclosureType.STABLECOIN_RESERVE in result.disclosures_required

    def test_is_cross_border(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx8", amount_eur=Decimal("100"),
            source_country="DE", destination_country="FR", token="USDC",
        )
        assert result.is_cross_border is True

    def test_not_cross_border(self):
        engine = MiCAComplianceEngine()
        result = engine.assess_transaction(
            tx_id="tx9", amount_eur=Decimal("100"),
            source_country="DE", destination_country="DE", token="USDC",
        )
        assert result.is_cross_border is False


# ============ Whitepaper Validation Tests ============


class TestWhitepaperValidation:
    def test_complete_whitepaper(self):
        engine = MiCAComplianceEngine()
        fields = {f: True for f in WhitepaperField}
        result = engine.validate_whitepaper("TEST", fields)
        assert result.is_valid is True
        assert result.missing_fields == []
        assert result.completeness_pct == 100.0

    def test_incomplete_whitepaper(self):
        engine = MiCAComplianceEngine()
        fields = {
            WhitepaperField.ISSUER_INFO: True,
            WhitepaperField.PROJECT_DESCRIPTION: True,
            WhitepaperField.RISKS: False,
        }
        result = engine.validate_whitepaper("TEST", fields)
        assert result.is_valid is False
        assert WhitepaperField.RISKS in result.missing_fields

    def test_empty_whitepaper(self):
        engine = MiCAComplianceEngine()
        result = engine.validate_whitepaper("TEST", {})
        assert result.is_valid is False
        assert len(result.missing_fields) == len(WhitepaperField)
        assert result.completeness_pct == 0.0

    def test_completeness_partial(self):
        engine = MiCAComplianceEngine()
        fields = {
            WhitepaperField.ISSUER_INFO: True,
            WhitepaperField.PROJECT_DESCRIPTION: True,
            WhitepaperField.RISKS: True,
            WhitepaperField.FEES: True,
        }
        result = engine.validate_whitepaper("TEST", fields)
        assert result.completeness_pct == 50.0  # 4/8


# ============ Risk Disclosure Tests ============


class TestRiskDisclosures:
    def test_general_risk_always_present(self):
        engine = MiCAComplianceEngine()
        disclosures = engine.generate_risk_disclosures("USDC")
        types = [d.disclosure_type for d in disclosures]
        assert DisclosureType.GENERAL_RISK in types

    def test_no_deposit_guarantee_always(self):
        engine = MiCAComplianceEngine()
        disclosures = engine.generate_risk_disclosures("BTC")
        types = [d.disclosure_type for d in disclosures]
        assert DisclosureType.NO_DEPOSIT_GUARANTEE in types

    def test_volatility_for_non_stablecoin(self):
        engine = MiCAComplianceEngine()
        disclosures = engine.generate_risk_disclosures("BTC")
        types = [d.disclosure_type for d in disclosures]
        assert DisclosureType.VOLATILITY_WARNING in types

    def test_no_volatility_for_stablecoin(self):
        engine = MiCAComplianceEngine()
        disclosures = engine.generate_risk_disclosures("USDC")
        types = [d.disclosure_type for d in disclosures]
        assert DisclosureType.VOLATILITY_WARNING not in types

    def test_stablecoin_reserve_disclosure(self):
        engine = MiCAComplianceEngine()
        disclosures = engine.generate_risk_disclosures("USDC")
        types = [d.disclosure_type for d in disclosures]
        assert DisclosureType.STABLECOIN_RESERVE in types

    def test_disclosure_language(self):
        engine = MiCAComplianceEngine()
        disclosures = engine.generate_risk_disclosures("USDC", language="de")
        assert all(d.language == "de" for d in disclosures)

    def test_disclosure_applicable_tokens(self):
        engine = MiCAComplianceEngine()
        disclosures = engine.generate_risk_disclosures("usdc")
        assert all("USDC" in d.applicable_tokens for d in disclosures)


# ============ SAR Report Tests ============


class TestSARReports:
    def test_create_eu_sar(self):
        engine = MiCAComplianceEngine()
        report = engine.create_sar_report(
            subject_id="wallet_123",
            amount_eur=Decimal("50000"),
            description="Suspicious layering pattern",
            region=SARRegion.EU,
        )
        assert isinstance(report, MiCASARReport)
        assert report.region == SARRegion.EU
        assert report.status == "pending"
        # Deadline should be ~72 hours from detection
        delta = report.deadline - report.detection_time
        assert abs(delta.total_seconds() - 72 * 3600) < 60

    def test_create_us_sar(self):
        engine = MiCAComplianceEngine()
        report = engine.create_sar_report(
            subject_id="wallet_456",
            amount_eur=Decimal("10000"),
            description="Structuring detected",
            region=SARRegion.US,
        )
        delta = report.deadline - report.detection_time
        assert abs(delta.total_seconds() - 30 * 86400) < 60

    def test_file_sar(self):
        engine = MiCAComplianceEngine()
        report = engine.create_sar_report(
            subject_id="wallet_789",
            amount_eur=Decimal("25000"),
            description="High-risk jurisdiction",
        )
        filed = engine.file_sar_report(report.report_id)
        assert filed.status == "filed"
        assert filed.filed_at is not None

    def test_file_sar_not_found(self):
        engine = MiCAComplianceEngine()
        with pytest.raises(ValueError, match="not found"):
            engine.file_sar_report("nonexistent")

    def test_overdue_sar(self):
        engine = MiCAComplianceEngine()
        # Create with past detection time
        past = datetime.now(UTC) - timedelta(days=5)
        report = engine.create_sar_report(
            subject_id="wallet_old",
            amount_eur=Decimal("100000"),
            description="Old activity",
            region=SARRegion.EU,
            detection_time=past,
        )
        assert report.is_overdue is True
        overdue = engine.get_overdue_sars()
        assert len(overdue) >= 1
        assert any(r.report_id == report.report_id for r in overdue)

    def test_filed_not_overdue(self):
        engine = MiCAComplianceEngine()
        past = datetime.now(UTC) - timedelta(days=5)
        report = engine.create_sar_report(
            subject_id="wallet_filed",
            amount_eur=Decimal("10000"),
            description="Already filed",
            region=SARRegion.EU,
            detection_time=past,
        )
        engine.file_sar_report(report.report_id)
        assert report.is_overdue is False

    def test_time_remaining(self):
        engine = MiCAComplianceEngine()
        report = engine.create_sar_report(
            subject_id="wallet_x",
            amount_eur=Decimal("5000"),
            description="Test",
            region=SARRegion.EU,
        )
        assert report.time_remaining > timedelta(0)

    def test_time_remaining_overdue(self):
        engine = MiCAComplianceEngine()
        past = datetime.now(UTC) - timedelta(days=10)
        report = engine.create_sar_report(
            subject_id="wallet_y",
            amount_eur=Decimal("5000"),
            description="Test",
            region=SARRegion.EU,
            detection_time=past,
        )
        assert report.time_remaining == timedelta(0)


# ============ CASP Authorization Tests ============


class TestCASPAuthorization:
    def _make_auth(self, **kwargs) -> CASPAuthorization:
        defaults = {
            "casp_id": "casp_1",
            "entity_name": "TestCASP",
            "home_member_state": "DE",
            "authorized_services": [CASPService.CUSTODY, CASPService.TRANSFER],
            "status": MiCAStatus.AUTHORIZED,
        }
        defaults.update(kwargs)
        return CASPAuthorization(**defaults)

    def test_authorized_home_state(self):
        engine = MiCAComplianceEngine()
        auth = self._make_auth()
        ok, reason = engine.check_casp_authorization(CASPService.CUSTODY, "DE", auth)
        assert ok is True
        assert "home member state" in reason

    def test_passported_to_eu(self):
        engine = MiCAComplianceEngine()
        auth = self._make_auth()
        ok, reason = engine.check_casp_authorization(CASPService.CUSTODY, "FR", auth)
        assert ok is True
        assert "Passported" in reason

    def test_unauthorized_casp(self):
        engine = MiCAComplianceEngine()
        auth = self._make_auth(status=MiCAStatus.NOT_APPLIED)
        ok, reason = engine.check_casp_authorization(CASPService.CUSTODY, "DE", auth)
        assert ok is False
        assert "not authorized" in reason

    def test_service_not_authorized(self):
        engine = MiCAComplianceEngine()
        auth = self._make_auth(authorized_services=[CASPService.CUSTODY])
        ok, reason = engine.check_casp_authorization(CASPService.ADVICE, "DE", auth)
        assert ok is False
        assert "not in authorized services" in reason

    def test_non_eu_country(self):
        engine = MiCAComplianceEngine()
        auth = self._make_auth()
        ok, reason = engine.check_casp_authorization(CASPService.CUSTODY, "US", auth)
        assert ok is False
        assert "non-EU/EEA" in reason

    def test_can_passport_property(self):
        auth = CASPAuthorization(
            casp_id="1", entity_name="Test", home_member_state="DE",
            status=MiCAStatus.AUTHORIZED,
        )
        assert auth.can_passport is True

    def test_cannot_passport_unauthorized(self):
        auth = CASPAuthorization(
            casp_id="1", entity_name="Test", home_member_state="DE",
            status=MiCAStatus.REVOKED,
        )
        assert auth.can_passport is False


# ============ Capital Requirements Tests ============


class TestCapitalRequirements:
    def test_custody_capital(self):
        engine = MiCAComplianceEngine()
        cap = engine.get_minimum_capital([CASPService.CUSTODY])
        assert cap == Decimal("150000")

    def test_advice_capital(self):
        engine = MiCAComplianceEngine()
        cap = engine.get_minimum_capital([CASPService.ADVICE])
        assert cap == Decimal("125000")

    def test_multiple_services_takes_max(self):
        engine = MiCAComplianceEngine()
        cap = engine.get_minimum_capital([CASPService.ADVICE, CASPService.CUSTODY])
        assert cap == Decimal("150000")

    def test_no_services_default(self):
        engine = MiCAComplianceEngine()
        cap = engine.get_minimum_capital([])
        assert cap == Decimal("50000")


# ============ Jurisdiction Tests ============


class TestJurisdiction:
    def test_eu_countries(self):
        engine = MiCAComplianceEngine()
        assert engine.is_eu_jurisdiction("DE") is True
        assert engine.is_eu_jurisdiction("FR") is True
        assert engine.is_eu_jurisdiction("IT") is True

    def test_eea_countries(self):
        engine = MiCAComplianceEngine()
        assert engine.is_eu_jurisdiction("NO") is True
        assert engine.is_eu_jurisdiction("IS") is True
        assert engine.is_eu_jurisdiction("LI") is True

    def test_non_eu(self):
        engine = MiCAComplianceEngine()
        assert engine.is_eu_jurisdiction("US") is False
        assert engine.is_eu_jurisdiction("JP") is False
        assert engine.is_eu_jurisdiction("KR") is False

    def test_is_eu_country_helper(self):
        assert is_eu_country("DE") is True
        assert is_eu_country("US") is False

    def test_case_insensitive(self):
        assert is_eu_country("de") is True


# ============ Constants Tests ============


class TestConstants:
    def test_eu_eea_count(self):
        # 27 EU + 3 EEA = 30
        assert len(EU_EEA_COUNTRIES) == 30

    def test_travel_rule_threshold(self):
        assert TRAVEL_RULE_THRESHOLD_EUR == Decimal("1000")

    def test_sar_deadline_eu(self):
        assert SAR_DEADLINES[SARRegion.EU] == timedelta(hours=72)

    def test_sar_deadline_us(self):
        assert SAR_DEADLINES[SARRegion.US] == timedelta(days=30)

    def test_stablecoin_classification_map(self):
        assert "USDC" in STABLECOIN_CLASSIFICATION
        assert "EURC" in STABLECOIN_CLASSIFICATION
        assert "DAI" in STABLECOIN_CLASSIFICATION

    def test_get_sar_deadline_helper(self):
        assert get_sar_deadline(SARRegion.EU) == timedelta(hours=72)


# ============ Enum Tests ============


class TestEnums:
    def test_casp_services(self):
        assert len(CASPService) == 8

    def test_crypto_asset_classes(self):
        assert len(CryptoAssetClass) == 4

    def test_mica_status_values(self):
        assert MiCAStatus.AUTHORIZED.value == "authorized"
        assert MiCAStatus.REVOKED.value == "revoked"

    def test_transaction_risk_values(self):
        assert TransactionRisk.PROHIBITED.value == "prohibited"

    def test_disclosure_types(self):
        assert len(DisclosureType) == 7

    def test_whitepaper_fields(self):
        assert len(WhitepaperField) == 8

    def test_sar_region_values(self):
        assert SARRegion.EU.value == "eu"
        assert SARRegion.US.value == "us"


# ============ Factory Tests ============


class TestFactory:
    def test_create_engine(self):
        engine = create_mica_engine()
        assert isinstance(engine, MiCAComplianceEngine)

    def test_create_engine_custom(self):
        engine = create_mica_engine(
            home_member_state="FR",
            authorized_services=[CASPService.CUSTODY],
        )
        assert engine._home_state == "FR"


# ============ Module Export Tests ============


class TestModuleExports:
    def test_imports_from_compliance(self):
        from sardis_compliance import (
            CASPAuthorization,
            CASPService,
            CryptoAssetClass,
            MiCAComplianceEngine,
            MiCAStatus,
            StablecoinAssessment,
            TransactionAssessment,
            TransactionRisk,
            WhitepaperField,
            classify_stablecoin,
            create_mica_engine,
            is_eu_country,
        )
        assert all([
            CASPAuthorization, CASPService, CryptoAssetClass,
            MiCAComplianceEngine, MiCAStatus, StablecoinAssessment,
            TransactionAssessment, TransactionRisk, WhitepaperField,
            classify_stablecoin, create_mica_engine, is_eu_country,
        ])
