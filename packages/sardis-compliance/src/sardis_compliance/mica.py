"""MiCA (Markets in Crypto-Assets Regulation) compliance module.

Implements EU Regulation 2023/1114 compliance checks for Crypto-Asset
Service Providers (CASPs). Covers:
- CASP authorization and classification
- Stablecoin classification (e-money tokens / asset-referenced tokens)
- Transaction monitoring with EU thresholds
- Suspicious transaction reporting (72h EU deadline)
- Risk disclosure generation for customers
- Travel Rule thresholds (EUR 1,000)
- Jurisdiction geofencing (EU/EEA member states)
- Whitepaper requirement validation
- Reserve adequacy checks for stablecoin issuers

Reference: https://eur-lex.europa.eu/eli/reg/2023/1114
Effective: 30 December 2024 (full application)
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============ Enums ============


class CASPService(str, Enum):
    """CASP service types per MiCA Article 3(1)(16)."""
    CUSTODY = "custody"
    TRADING_PLATFORM = "trading_platform"
    EXCHANGE = "exchange"
    ORDER_EXECUTION = "order_execution"
    PLACEMENT = "placement"
    TRANSFER = "transfer"
    ADVICE = "advice"
    PORTFOLIO_MANAGEMENT = "portfolio_management"


class CryptoAssetClass(str, Enum):
    """Crypto-asset classification per MiCA Title III/IV."""
    E_MONEY_TOKEN = "e_money_token"           # Title IV — pegged to single fiat
    ASSET_REFERENCED_TOKEN = "asset_referenced_token"  # Title III — pegged to basket/commodity
    UTILITY_TOKEN = "utility_token"           # Title II — access to service
    OTHER_CRYPTO_ASSET = "other_crypto_asset"  # Catch-all (e.g., BTC, ETH)


class MiCAStatus(str, Enum):
    """Authorization status."""
    NOT_APPLIED = "not_applied"
    APPLICATION_PENDING = "application_pending"
    AUTHORIZED = "authorized"
    RESTRICTED = "restricted"
    REVOKED = "revoked"


class TransactionRisk(str, Enum):
    """MiCA transaction risk classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


class DisclosureType(str, Enum):
    """Risk disclosure types per MiCA Article 66."""
    GENERAL_RISK = "general_risk"
    VOLATILITY_WARNING = "volatility_warning"
    LOSS_OF_VALUE = "loss_of_value"
    NO_DEPOSIT_GUARANTEE = "no_deposit_guarantee"
    REGULATORY_STATUS = "regulatory_status"
    STABLECOIN_RESERVE = "stablecoin_reserve"
    LIQUIDITY_RISK = "liquidity_risk"


class WhitepaperField(str, Enum):
    """Required whitepaper fields per MiCA Article 6."""
    ISSUER_INFO = "issuer_info"
    PROJECT_DESCRIPTION = "project_description"
    RIGHTS_OBLIGATIONS = "rights_obligations"
    TECHNOLOGY = "technology"
    RISKS = "risks"
    FEES = "fees"
    ENVIRONMENTAL_IMPACT = "environmental_impact"
    COMPLAINT_PROCEDURE = "complaint_procedure"


class SARRegion(str, Enum):
    """SAR regulatory region for filing deadlines."""
    EU = "eu"        # 72 hours
    US = "us"        # 30 days (FinCEN)
    UK = "uk"        # ASAP + 7 business days


# ============ Constants ============

# EU/EEA member state ISO codes
EU_EEA_COUNTRIES: frozenset[str] = frozenset({
    # EU 27
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    # EEA (non-EU)
    "IS", "LI", "NO",
})

# MiCA Travel Rule threshold (Article 68 + TFR Regulation)
TRAVEL_RULE_THRESHOLD_EUR = Decimal("1000")

# Significant stablecoin thresholds (Article 43/56)
SIGNIFICANT_EMT_RESERVE_EUR = Decimal("5000000000")   # 5B EUR
SIGNIFICANT_ART_RESERVE_EUR = Decimal("5000000000")   # 5B EUR
SIGNIFICANT_DAILY_TX_VOLUME = 2_500_000  # 2.5M transactions/day
SIGNIFICANT_DAILY_TX_VALUE_EUR = Decimal("500000000")  # 500M EUR/day

# Known stablecoin classifications
STABLECOIN_CLASSIFICATION: dict[str, CryptoAssetClass] = {
    "USDC": CryptoAssetClass.E_MONEY_TOKEN,
    "EURC": CryptoAssetClass.E_MONEY_TOKEN,
    "USDT": CryptoAssetClass.E_MONEY_TOKEN,
    "PYUSD": CryptoAssetClass.E_MONEY_TOKEN,
    "DAI": CryptoAssetClass.ASSET_REFERENCED_TOKEN,  # multi-collateral
    "FRAX": CryptoAssetClass.ASSET_REFERENCED_TOKEN,
}

# SAR filing deadlines by region
SAR_DEADLINES: dict[SARRegion, timedelta] = {
    SARRegion.EU: timedelta(hours=72),
    SARRegion.US: timedelta(days=30),
    SARRegion.UK: timedelta(days=7),
}


# ============ Data Classes ============


@dataclass
class CASPAuthorization:
    """CASP authorization record per MiCA Title V."""
    casp_id: str
    entity_name: str
    home_member_state: str  # ISO country code
    authorized_services: list[CASPService] = field(default_factory=list)
    status: MiCAStatus = MiCAStatus.NOT_APPLIED
    authorization_date: datetime | None = None
    nca_reference: str | None = None  # National Competent Authority ref
    passported_countries: list[str] = field(default_factory=list)
    prudential_requirements_met: bool = False
    minimum_capital_eur: Decimal = Decimal("0")
    complaints_procedure: bool = False
    governance_arrangements: bool = False

    @property
    def is_authorized(self) -> bool:
        return self.status == MiCAStatus.AUTHORIZED

    @property
    def can_passport(self) -> bool:
        """CASPs authorized in one EU state can passport to others."""
        return self.is_authorized and self.home_member_state in EU_EEA_COUNTRIES


@dataclass
class StablecoinAssessment:
    """Stablecoin classification and compliance assessment."""
    token_symbol: str
    asset_class: CryptoAssetClass
    issuer_name: str | None = None
    reference_currency: str | None = None  # ISO 4217 for EMTs
    is_significant: bool = False
    reserve_amount_eur: Decimal = Decimal("0")
    daily_tx_volume: int = 0
    daily_tx_value_eur: Decimal = Decimal("0")
    has_whitepaper: bool = False
    issuer_authorized: bool = False
    reserve_compliant: bool = False
    redemption_rights: bool = False

    @property
    def requires_eba_supervision(self) -> bool:
        """Significant EMTs/ARTs require EBA (not NCA) supervision."""
        if not self.is_significant:
            return False
        return self.asset_class in (
            CryptoAssetClass.E_MONEY_TOKEN,
            CryptoAssetClass.ASSET_REFERENCED_TOKEN,
        )

    @property
    def compliance_score(self) -> int:
        """0-100 compliance score based on met requirements."""
        score = 0
        if self.has_whitepaper:
            score += 25
        if self.issuer_authorized:
            score += 25
        if self.reserve_compliant:
            score += 25
        if self.redemption_rights:
            score += 25
        return score


@dataclass
class TransactionAssessment:
    """MiCA transaction compliance assessment."""
    tx_id: str
    amount_eur: Decimal
    source_country: str
    destination_country: str
    token: str
    risk: TransactionRisk = TransactionRisk.LOW
    requires_travel_rule: bool = False
    requires_enhanced_monitoring: bool = False
    disclosures_required: list[DisclosureType] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_eu_transaction(self) -> bool:
        return (
            self.source_country in EU_EEA_COUNTRIES
            or self.destination_country in EU_EEA_COUNTRIES
        )

    @property
    def is_cross_border(self) -> bool:
        return self.source_country != self.destination_country


@dataclass
class WhitepaperValidation:
    """Crypto-asset whitepaper validation result."""
    token_symbol: str
    fields_present: dict[WhitepaperField, bool] = field(default_factory=dict)
    is_valid: bool = False
    missing_fields: list[WhitepaperField] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def completeness_pct(self) -> float:
        if not self.fields_present:
            return 0.0
        present = sum(1 for v in self.fields_present.values() if v)
        return (present / len(WhitepaperField)) * 100


@dataclass
class RiskDisclosure:
    """Customer risk disclosure per MiCA Article 66."""
    disclosure_type: DisclosureType
    text: str
    language: str = "en"
    applicable_tokens: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MiCASARReport:
    """Suspicious transaction report under MiCA/EU framework."""
    report_id: str
    region: SARRegion
    detection_time: datetime
    deadline: datetime
    subject_id: str
    amount_eur: Decimal
    description: str
    status: str = "pending"  # pending, filed, overdue
    filed_at: datetime | None = None

    @property
    def is_overdue(self) -> bool:
        if self.status == "filed":
            return False
        return datetime.now(UTC) > self.deadline

    @property
    def time_remaining(self) -> timedelta:
        remaining = self.deadline - datetime.now(UTC)
        return max(remaining, timedelta(0))


# ============ Service Classes ============


class MiCAComplianceEngine:
    """Core MiCA compliance engine.

    Provides transaction assessment, stablecoin classification,
    CASP authorization checks, and risk disclosure generation
    for EU/EEA operations under MiCA regulation.
    """

    def __init__(
        self,
        home_member_state: str = "DE",
        authorized_services: list[CASPService] | None = None,
    ):
        self._home_state = home_member_state.upper()
        self._authorized_services = authorized_services or []
        self._sar_reports: dict[str, MiCASARReport] = {}

    def classify_token(self, symbol: str) -> CryptoAssetClass:
        """Classify a crypto-asset under MiCA taxonomy.

        Args:
            symbol: Token symbol (e.g., "USDC", "BTC")

        Returns:
            CryptoAssetClass classification
        """
        symbol_upper = symbol.upper()
        if symbol_upper in STABLECOIN_CLASSIFICATION:
            return STABLECOIN_CLASSIFICATION[symbol_upper]
        return CryptoAssetClass.OTHER_CRYPTO_ASSET

    def assess_stablecoin(
        self,
        token_symbol: str,
        issuer_name: str | None = None,
        reference_currency: str | None = None,
        reserve_amount_eur: Decimal = Decimal("0"),
        daily_tx_volume: int = 0,
        daily_tx_value_eur: Decimal = Decimal("0"),
        has_whitepaper: bool = False,
        issuer_authorized: bool = False,
        reserve_compliant: bool = False,
        redemption_rights: bool = False,
    ) -> StablecoinAssessment:
        """Assess stablecoin compliance under MiCA Title III/IV.

        Args:
            token_symbol: Token symbol
            issuer_name: Name of the token issuer
            reference_currency: Fiat currency reference (for EMTs)
            reserve_amount_eur: Total reserve value in EUR
            daily_tx_volume: Average daily transaction count
            daily_tx_value_eur: Average daily transaction value in EUR
            has_whitepaper: Whether compliant whitepaper exists
            issuer_authorized: Whether issuer holds CASP/EMI authorization
            reserve_compliant: Whether reserves meet MiCA requirements
            redemption_rights: Whether 1:1 redemption at par is guaranteed
        """
        asset_class = self.classify_token(token_symbol)

        # Determine significance per Article 43/56
        is_significant = False
        if asset_class in (CryptoAssetClass.E_MONEY_TOKEN, CryptoAssetClass.ASSET_REFERENCED_TOKEN):
            threshold = (
                SIGNIFICANT_EMT_RESERVE_EUR
                if asset_class == CryptoAssetClass.E_MONEY_TOKEN
                else SIGNIFICANT_ART_RESERVE_EUR
            )
            if reserve_amount_eur >= threshold:
                is_significant = True
            if daily_tx_volume >= SIGNIFICANT_DAILY_TX_VOLUME:
                is_significant = True
            if daily_tx_value_eur >= SIGNIFICANT_DAILY_TX_VALUE_EUR:
                is_significant = True

        return StablecoinAssessment(
            token_symbol=token_symbol.upper(),
            asset_class=asset_class,
            issuer_name=issuer_name,
            reference_currency=reference_currency,
            is_significant=is_significant,
            reserve_amount_eur=reserve_amount_eur,
            daily_tx_volume=daily_tx_volume,
            daily_tx_value_eur=daily_tx_value_eur,
            has_whitepaper=has_whitepaper,
            issuer_authorized=issuer_authorized,
            reserve_compliant=reserve_compliant,
            redemption_rights=redemption_rights,
        )

    def assess_transaction(
        self,
        tx_id: str,
        amount_eur: Decimal,
        source_country: str,
        destination_country: str,
        token: str,
    ) -> TransactionAssessment:
        """Assess a transaction for MiCA compliance.

        Evaluates travel rule applicability, enhanced monitoring
        requirements, risk classification, and required disclosures.

        Args:
            tx_id: Transaction identifier
            amount_eur: Transaction amount in EUR
            source_country: ISO country code of sender
            destination_country: ISO country code of recipient
            token: Token symbol used
        """
        source = source_country.upper()
        dest = destination_country.upper()
        flags: list[str] = []
        disclosures: list[DisclosureType] = []

        # Travel Rule (TFR): applies to transfers >= EUR 1,000
        requires_travel_rule = amount_eur >= TRAVEL_RULE_THRESHOLD_EUR

        # Determine risk level
        risk = TransactionRisk.LOW
        requires_enhanced = False

        # Cross-border with non-EU raises risk
        is_eu_src = source in EU_EEA_COUNTRIES
        is_eu_dst = dest in EU_EEA_COUNTRIES

        if is_eu_src or is_eu_dst:
            disclosures.append(DisclosureType.GENERAL_RISK)
            disclosures.append(DisclosureType.NO_DEPOSIT_GUARANTEE)

        if (is_eu_src or is_eu_dst) and not (is_eu_src and is_eu_dst):
            risk = TransactionRisk.MEDIUM
            flags.append("cross_border_eu_non_eu")
            requires_enhanced = True

        # High-value triggers enhanced monitoring
        if amount_eur >= Decimal("15000"):
            risk = TransactionRisk.HIGH
            flags.append("high_value_above_15k_eur")
            requires_enhanced = True
            disclosures.append(DisclosureType.LOSS_OF_VALUE)

        # Stablecoin-specific disclosures
        asset_class = self.classify_token(token)
        if asset_class in (CryptoAssetClass.E_MONEY_TOKEN, CryptoAssetClass.ASSET_REFERENCED_TOKEN):
            disclosures.append(DisclosureType.STABLECOIN_RESERVE)

        # Neither source nor destination is EU — MiCA does not directly apply
        if not is_eu_src and not is_eu_dst:
            flags.append("non_eu_transaction")

        return TransactionAssessment(
            tx_id=tx_id,
            amount_eur=amount_eur,
            source_country=source,
            destination_country=dest,
            token=token.upper(),
            risk=risk,
            requires_travel_rule=requires_travel_rule,
            requires_enhanced_monitoring=requires_enhanced,
            disclosures_required=disclosures,
            flags=flags,
        )

    def validate_whitepaper(
        self,
        token_symbol: str,
        fields_present: dict[WhitepaperField, bool],
    ) -> WhitepaperValidation:
        """Validate a crypto-asset whitepaper against MiCA Article 6 requirements.

        All 8 fields are mandatory for any crypto-asset whitepaper
        published in the EU.

        Args:
            token_symbol: Token symbol
            fields_present: Mapping of required fields to presence boolean
        """
        missing = [
            f for f in WhitepaperField
            if not fields_present.get(f, False)
        ]
        is_valid = len(missing) == 0

        return WhitepaperValidation(
            token_symbol=token_symbol.upper(),
            fields_present=fields_present,
            is_valid=is_valid,
            missing_fields=missing,
        )

    def generate_risk_disclosures(
        self,
        token: str,
        language: str = "en",
    ) -> list[RiskDisclosure]:
        """Generate required risk disclosures for a crypto-asset.

        MiCA Article 66 requires CASPs to warn customers about risks
        before any transaction.

        Args:
            token: Token symbol
            language: ISO language code
        """
        asset_class = self.classify_token(token)
        disclosures: list[RiskDisclosure] = []

        # General risk — always required
        disclosures.append(RiskDisclosure(
            disclosure_type=DisclosureType.GENERAL_RISK,
            text=(
                "Crypto-assets are not covered by deposit guarantee schemes. "
                "You may lose the entirety of your investment."
            ),
            language=language,
            applicable_tokens=[token.upper()],
        ))

        # Volatility warning for non-stablecoins
        if asset_class == CryptoAssetClass.OTHER_CRYPTO_ASSET:
            disclosures.append(RiskDisclosure(
                disclosure_type=DisclosureType.VOLATILITY_WARNING,
                text=(
                    "This crypto-asset is subject to high price volatility. "
                    "Past performance is not indicative of future results."
                ),
                language=language,
                applicable_tokens=[token.upper()],
            ))

        # Stablecoin reserve disclosure
        if asset_class in (CryptoAssetClass.E_MONEY_TOKEN, CryptoAssetClass.ASSET_REFERENCED_TOKEN):
            disclosures.append(RiskDisclosure(
                disclosure_type=DisclosureType.STABLECOIN_RESERVE,
                text=(
                    "This stablecoin's value depends on the adequacy of reserves "
                    "maintained by its issuer. Depegging risk exists."
                ),
                language=language,
                applicable_tokens=[token.upper()],
            ))

        # No deposit guarantee — always required
        disclosures.append(RiskDisclosure(
            disclosure_type=DisclosureType.NO_DEPOSIT_GUARANTEE,
            text=(
                "Crypto-assets held through this service are not covered by "
                "the Deposit Guarantee Scheme (Directive 2014/49/EU) or the "
                "Investor Compensation Scheme (Directive 97/9/EC)."
            ),
            language=language,
            applicable_tokens=[token.upper()],
        ))

        return disclosures

    def create_sar_report(
        self,
        subject_id: str,
        amount_eur: Decimal,
        description: str,
        region: SARRegion = SARRegion.EU,
        detection_time: datetime | None = None,
    ) -> MiCASARReport:
        """Create a suspicious activity report with region-specific deadline.

        EU MiCA requires filing within 72 hours of detection.
        FinCEN (US) allows 30 days. UK requires ASAP + 7 business days.

        Args:
            subject_id: ID of the suspected entity
            amount_eur: Transaction amount in EUR
            description: Description of suspicious activity
            region: Regulatory region for deadline calculation
            detection_time: When activity was detected (defaults to now)
        """
        now = detection_time or datetime.now(UTC)
        deadline = now + SAR_DEADLINES[region]

        report = MiCASARReport(
            report_id=f"sar_{uuid.uuid4().hex[:16]}",
            region=region,
            detection_time=now,
            deadline=deadline,
            subject_id=subject_id,
            amount_eur=amount_eur,
            description=description,
        )

        self._sar_reports[report.report_id] = report
        logger.info(
            f"Created SAR {report.report_id} for {subject_id}, "
            f"deadline: {deadline.isoformat()} ({region.value})"
        )
        return report

    def file_sar_report(self, report_id: str) -> MiCASARReport:
        """Mark a SAR as filed with the relevant authority.

        Args:
            report_id: SAR report identifier

        Raises:
            ValueError: If report not found
        """
        report = self._sar_reports.get(report_id)
        if not report:
            raise ValueError(f"SAR report not found: {report_id}")
        report.status = "filed"
        report.filed_at = datetime.now(UTC)
        logger.info(f"SAR {report_id} filed at {report.filed_at.isoformat()}")
        return report

    def get_overdue_sars(self) -> list[MiCASARReport]:
        """Get all SAR reports that are past their filing deadline."""
        return [r for r in self._sar_reports.values() if r.is_overdue]

    def check_casp_authorization(
        self,
        service: CASPService,
        target_country: str,
        authorization: CASPAuthorization,
    ) -> tuple[bool, str]:
        """Check if a CASP is authorized to offer a service in a country.

        Args:
            service: The CASP service being offered
            target_country: ISO country code where service is offered
            authorization: The CASP's authorization record

        Returns:
            Tuple of (is_authorized, reason)
        """
        target = target_country.upper()

        if not authorization.is_authorized:
            return False, "CASP is not authorized under MiCA"

        if service not in authorization.authorized_services:
            return False, f"Service '{service.value}' not in authorized services"

        # Home member state — always allowed
        if target == authorization.home_member_state:
            return True, "Authorized in home member state"

        # Passporting within EU/EEA
        if target in EU_EEA_COUNTRIES:
            if authorization.can_passport:
                return True, f"Passported to {target} from {authorization.home_member_state}"
            return False, f"Cannot passport to {target}: not an EU/EEA CASP"

        # Non-EU/EEA — MiCA doesn't cover, local regulations apply
        return False, f"MiCA does not authorize operations in non-EU/EEA country {target}"

    def get_minimum_capital(self, services: list[CASPService]) -> Decimal:
        """Get minimum capital requirement for a set of CASP services.

        MiCA Article 67 specifies minimum capital based on service type:
        - Custody/Trading platform: EUR 150,000
        - Exchange/Order execution: EUR 150,000
        - Advice/Portfolio management: EUR 125,000
        - Transfer services: EUR 150,000
        - Other: EUR 50,000
        """
        capital_map: dict[CASPService, Decimal] = {
            CASPService.CUSTODY: Decimal("150000"),
            CASPService.TRADING_PLATFORM: Decimal("150000"),
            CASPService.EXCHANGE: Decimal("150000"),
            CASPService.ORDER_EXECUTION: Decimal("150000"),
            CASPService.TRANSFER: Decimal("150000"),
            CASPService.PLACEMENT: Decimal("125000"),
            CASPService.ADVICE: Decimal("125000"),
            CASPService.PORTFOLIO_MANAGEMENT: Decimal("125000"),
        }
        if not services:
            return Decimal("50000")
        return max(capital_map.get(s, Decimal("50000")) for s in services)

    def is_eu_jurisdiction(self, country_code: str) -> bool:
        """Check if a country is in the EU/EEA (MiCA jurisdiction)."""
        return country_code.upper() in EU_EEA_COUNTRIES


def is_eu_country(country_code: str) -> bool:
    """Check if an ISO country code is an EU/EEA member state."""
    return country_code.upper() in EU_EEA_COUNTRIES


def classify_stablecoin(symbol: str) -> CryptoAssetClass:
    """Classify a stablecoin under MiCA taxonomy.

    Returns CryptoAssetClass.OTHER_CRYPTO_ASSET if not a known stablecoin.
    """
    return STABLECOIN_CLASSIFICATION.get(
        symbol.upper(), CryptoAssetClass.OTHER_CRYPTO_ASSET
    )


def get_sar_deadline(region: SARRegion) -> timedelta:
    """Get the SAR filing deadline for a regulatory region."""
    return SAR_DEADLINES[region]


def create_mica_engine(
    home_member_state: str = "DE",
    authorized_services: list[CASPService] | None = None,
) -> MiCAComplianceEngine:
    """Factory function to create a MiCAComplianceEngine."""
    return MiCAComplianceEngine(
        home_member_state=home_member_state,
        authorized_services=authorized_services,
    )
