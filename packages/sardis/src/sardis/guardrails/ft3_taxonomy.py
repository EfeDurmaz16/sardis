"""FT3 (Fraud Tools, Tactics, Techniques) taxonomy for Sardis.

Implements Stripe's open-source FT3 fraud classification taxonomy
(modeled after MITRE ATT&CK) extended with agent-economy-specific
techniques for the Sardis Payment OS.

Standard FT3 defines 12 tactics and 137 techniques for classifying
financial fraud. Sardis adds 3 agent-specific tactics (TA13–TA15)
covering agent impersonation, policy evasion, and autonomous fraud.

References:
- Stripe FT3: https://github.com/stripe/ft3
- MITRE ATT&CK: https://attack.mitre.org/
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============ Constants ============

FT3_VERSION = "1.0.0"
FT3_STANDARD_TACTIC_COUNT = 12
FT3_AGENT_TACTIC_COUNT = 3
HIGH_CONFIDENCE_THRESHOLD = 0.8
SARDIS_TECHNIQUE_PREFIX = "T13"


# ============ Enums ============


class FT3Tactic(str, Enum):
    """FT3 fraud tactics — high-level adversary goals.

    TA01–TA12 are standard Stripe FT3 tactics.
    TA13–TA15 are Sardis agent-economy extensions.
    """
    ACCOUNT_CREATION_FRAUD = "TA01"
    ACCOUNT_TAKEOVER = "TA02"
    CARD_FRAUD = "TA03"
    IDENTITY_FRAUD = "TA04"
    MONEY_LAUNDERING = "TA05"
    MERCHANT_FRAUD = "TA06"
    PROMO_ABUSE = "TA07"
    REFUND_FRAUD = "TA08"
    WIRE_FRAUD = "TA09"
    CHECK_FRAUD = "TA10"
    LOAN_FRAUD = "TA11"
    INSURANCE_FRAUD = "TA12"
    # Agent-economy extensions
    AGENT_IMPERSONATION = "TA13"
    POLICY_EVASION = "TA14"
    AUTONOMOUS_FRAUD = "TA15"


class FT3Severity(str, Enum):
    """Severity level for a fraud technique."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FT3MitigationStatus(str, Enum):
    """Deployment status of a mitigation control."""
    ACTIVE = "active"
    PLANNED = "planned"
    NOT_APPLICABLE = "n/a"


# ============ Data Classes ============


@dataclass
class FT3Technique:
    """A specific fraud technique within a tactic.

    Techniques are the atomic unit of the FT3 taxonomy — each
    describes a concrete method an adversary uses to achieve a
    tactic's goal.
    """
    technique_id: str           # e.g. "T0101"
    name: str
    description: str
    tactic: FT3Tactic
    severity: FT3Severity
    indicators: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    is_agent_specific: bool = False

    @property
    def full_id(self) -> str:
        """Fully-qualified technique identifier, e.g. 'FT3-T0101'."""
        return f"FT3-{self.technique_id}"


@dataclass
class FT3Event:
    """A detected fraud event classified by FT3 technique.

    Events are recorded when the system observes activity matching
    a registered technique's indicators.
    """
    event_id: str
    technique_id: str
    agent_id: str = ""
    transaction_id: str = ""
    confidence: float = 0.0     # 0.0–1.0
    details: dict = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_high_confidence(self) -> bool:
        """True when confidence meets or exceeds the high-confidence threshold."""
        return self.confidence >= HIGH_CONFIDENCE_THRESHOLD


@dataclass
class FT3Mitigation:
    """A control that mitigates one or more fraud techniques."""
    mitigation_id: str
    name: str
    description: str
    technique_ids: list[str] = field(default_factory=list)
    status: FT3MitigationStatus = FT3MitigationStatus.ACTIVE


@dataclass
class FT3TaxonomyStats:
    """Summary statistics for the taxonomy registry."""
    total_tactics: int
    total_techniques: int
    agent_specific_count: int
    coverage_by_tactic: dict[str, int] = field(default_factory=dict)


# ============ Registry ============


class FT3TaxonomyRegistry:
    """Central registry for FT3 techniques, mitigations, and events.

    Use ``create_ft3_registry()`` factory for convenience.
    """

    def __init__(self) -> None:
        self._techniques: dict[str, FT3Technique] = {}
        self._events: list[FT3Event] = []
        self._mitigations: dict[str, FT3Mitigation] = {}

    # -- Registration --

    def register_technique(self, technique: FT3Technique) -> FT3Technique:
        """Register a technique. Raises ValueError on duplicate ID."""
        if technique.technique_id in self._techniques:
            raise ValueError(
                f"Duplicate technique ID: {technique.technique_id}"
            )
        self._techniques[technique.technique_id] = technique
        logger.debug("Registered technique %s: %s", technique.full_id, technique.name)
        return technique

    def register_mitigation(self, mitigation: FT3Mitigation) -> FT3Mitigation:
        """Register a mitigation control."""
        self._mitigations[mitigation.mitigation_id] = mitigation
        return mitigation

    # -- Queries --

    def get_technique(self, technique_id: str) -> FT3Technique | None:
        """Look up a technique by ID, or None if not found."""
        return self._techniques.get(technique_id)

    def get_techniques_for_tactic(self, tactic: FT3Tactic) -> list[FT3Technique]:
        """Return all techniques belonging to a tactic."""
        return [t for t in self._techniques.values() if t.tactic == tactic]

    def get_agent_specific_techniques(self) -> list[FT3Technique]:
        """Return techniques flagged as agent-specific."""
        return [t for t in self._techniques.values() if t.is_agent_specific]

    def search_techniques(self, query: str) -> list[FT3Technique]:
        """Case-insensitive search across technique name and description."""
        q = query.lower()
        return [
            t for t in self._techniques.values()
            if q in t.name.lower() or q in t.description.lower()
        ]

    # -- Events --

    def record_event(
        self,
        technique_id: str,
        agent_id: str = "",
        transaction_id: str = "",
        confidence: float = 0.0,
        details: dict | None = None,
    ) -> FT3Event:
        """Record a fraud event. Raises ValueError if technique is unknown."""
        if technique_id not in self._techniques:
            raise ValueError(f"Unknown technique: {technique_id}")
        event = FT3Event(
            event_id=uuid.uuid4().hex[:12],
            technique_id=technique_id,
            agent_id=agent_id,
            transaction_id=transaction_id,
            confidence=confidence,
            details=details or {},
        )
        self._events.append(event)
        logger.info(
            "FT3 event %s: technique=%s agent=%s confidence=%.2f",
            event.event_id, technique_id, agent_id, confidence,
        )
        return event

    def get_events(
        self,
        technique_id: str | None = None,
        agent_id: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[FT3Event]:
        """Filtered event query."""
        results = self._events
        if technique_id is not None:
            results = [e for e in results if e.technique_id == technique_id]
        if agent_id is not None:
            results = [e for e in results if e.agent_id == agent_id]
        if min_confidence > 0.0:
            results = [e for e in results if e.confidence >= min_confidence]
        return results

    # -- Stats --

    def get_stats(self) -> FT3TaxonomyStats:
        """Compute summary statistics."""
        coverage: dict[str, int] = {}
        for t in self._techniques.values():
            tactic_val = t.tactic.value
            coverage[tactic_val] = coverage.get(tactic_val, 0) + 1

        return FT3TaxonomyStats(
            total_tactics=len({t.tactic for t in self._techniques.values()}),
            total_techniques=len(self._techniques),
            agent_specific_count=len(self.get_agent_specific_techniques()),
            coverage_by_tactic=coverage,
        )

    # -- Properties --

    @property
    def technique_count(self) -> int:
        return len(self._techniques)

    @property
    def event_count(self) -> int:
        return len(self._events)

    # -- Standard Taxonomy --

    def load_standard_taxonomy(self) -> None:
        """Populate the registry with the built-in FT3 + Sardis techniques."""
        techniques = _build_standard_techniques()
        for t in techniques:
            self.register_technique(t)
        logger.info("Loaded %d standard FT3 techniques", len(techniques))


# ============ Standard Techniques ============


def _build_standard_techniques() -> list[FT3Technique]:
    """Return the built-in technique catalogue."""
    return [
        # ---- TA01 Account Creation Fraud ----
        FT3Technique(
            technique_id="T0101",
            name="Synthetic Identity",
            description="Fabricated identity combining real and fake data to create fraudulent accounts.",
            tactic=FT3Tactic.ACCOUNT_CREATION_FRAUD,
            severity=FT3Severity.HIGH,
            indicators=[
                "Mismatched SSN/name combinations",
                "Newly created email addresses",
                "Phone number cycling across applications",
            ],
            mitigations=[
                "Cross-reference identity elements against bureau data",
                "Velocity checks on shared identity attributes",
            ],
        ),
        FT3Technique(
            technique_id="T0102",
            name="Bot Registration",
            description="Automated mass account creation using scripted or headless browser tools.",
            tactic=FT3Tactic.ACCOUNT_CREATION_FRAUD,
            severity=FT3Severity.MEDIUM,
            indicators=[
                "Rapid sequential signups from same IP range",
                "Identical device fingerprints",
                "Missing or uniform browser entropy",
            ],
            mitigations=[
                "CAPTCHA challenges on registration",
                "Device fingerprint deduplication",
                "Rate limit account creation per IP/device",
            ],
        ),

        # ---- TA02 Account Takeover ----
        FT3Technique(
            technique_id="T0201",
            name="Credential Stuffing",
            description="Reusing leaked username/password pairs from data breaches to hijack accounts.",
            tactic=FT3Tactic.ACCOUNT_TAKEOVER,
            severity=FT3Severity.HIGH,
            indicators=[
                "High-volume login failures from distributed IPs",
                "Known breach-sourced credential patterns",
                "Login from unfamiliar geolocation",
            ],
            mitigations=[
                "Credential breach database checks (HaveIBeenPwned)",
                "Adaptive MFA on suspicious login",
                "Rate limit authentication attempts",
            ],
        ),
        FT3Technique(
            technique_id="T0202",
            name="SIM Swap",
            description="Social engineering carrier to port victim's phone number for 2FA bypass.",
            tactic=FT3Tactic.ACCOUNT_TAKEOVER,
            severity=FT3Severity.CRITICAL,
            indicators=[
                "Sudden 2FA delivery failure",
                "Carrier port-out notification",
                "Password reset immediately after SIM change",
            ],
            mitigations=[
                "Authenticator app instead of SMS 2FA",
                "Port-freeze / SIM-lock with carrier",
                "Behavioral biometrics post-login",
            ],
        ),

        # ---- TA03 Card Fraud ----
        FT3Technique(
            technique_id="T0301",
            name="Card Testing",
            description="Small-value transactions to validate stolen card numbers before larger fraud.",
            tactic=FT3Tactic.CARD_FRAUD,
            severity=FT3Severity.HIGH,
            indicators=[
                "Micro-transactions ($0.01–$1.00) on new cards",
                "Rapid sequential authorizations",
                "Decline-then-retry patterns",
            ],
            mitigations=[
                "Velocity rules on low-value authorizations",
                "Block rapid retry on declined cards",
                "CVC/AVS mismatch blocking",
            ],
        ),
        FT3Technique(
            technique_id="T0302",
            name="BIN Attack",
            description="Generating valid card numbers by iterating through a Bank Identification Number range.",
            tactic=FT3Tactic.CARD_FRAUD,
            severity=FT3Severity.CRITICAL,
            indicators=[
                "Sequential PAN patterns in authorization requests",
                "High decline rates from single BIN",
                "Distributed source IPs with same BIN prefix",
            ],
            mitigations=[
                "BIN-level velocity monitoring",
                "Intelligent decline thresholds per BIN",
                "Network-level BIN attack detection (Visa/MC alerts)",
            ],
        ),

        # ---- TA04 Identity Fraud ----
        FT3Technique(
            technique_id="T0401",
            name="Document Forgery",
            description="Fabricated or altered identity documents used for KYC verification.",
            tactic=FT3Tactic.IDENTITY_FRAUD,
            severity=FT3Severity.HIGH,
            indicators=[
                "Image metadata inconsistencies",
                "Template-matching against known forgery patterns",
                "Mismatched document fonts or security features",
            ],
            mitigations=[
                "Document authenticity verification (NFC chip, hologram)",
                "Liveness detection during selfie verification",
                "Cross-reference with government databases",
            ],
        ),
        FT3Technique(
            technique_id="T0402",
            name="Identity Theft",
            description="Using stolen personal information to impersonate a real individual.",
            tactic=FT3Tactic.IDENTITY_FRAUD,
            severity=FT3Severity.CRITICAL,
            indicators=[
                "Application from known compromised identity",
                "Address or phone recently changed at bureau",
                "Activity inconsistent with identity holder profile",
            ],
            mitigations=[
                "Knowledge-based authentication (KBA)",
                "Credit freeze / fraud alert monitoring",
                "Behavioral analysis against historical profile",
            ],
        ),

        # ---- TA05 Money Laundering ----
        FT3Technique(
            technique_id="T0501",
            name="Layering",
            description="Complex transaction chains designed to obscure the origin of illicit funds.",
            tactic=FT3Tactic.MONEY_LAUNDERING,
            severity=FT3Severity.CRITICAL,
            indicators=[
                "Circular fund flows through multiple wallets",
                "Rapid cross-chain transfers",
                "Transactions with no apparent economic purpose",
            ],
            mitigations=[
                "Graph-based transaction analysis",
                "Cross-chain flow tracing",
                "SAR filing on detected layering patterns",
            ],
        ),
        FT3Technique(
            technique_id="T0502",
            name="Smurfing",
            description="Breaking large amounts into small transactions to evade reporting thresholds.",
            tactic=FT3Tactic.MONEY_LAUNDERING,
            severity=FT3Severity.HIGH,
            indicators=[
                "Multiple transactions just below reporting limits",
                "Structured deposits across time windows",
                "Same beneficiary receiving from many senders",
            ],
            mitigations=[
                "Aggregate transaction monitoring per entity",
                "Structuring detection algorithms",
                "CTR/SAR auto-filing on threshold patterns",
            ],
        ),

        # ---- TA06 Merchant Fraud ----
        FT3Technique(
            technique_id="T0601",
            name="Phantom Merchant",
            description="Creating a fictitious merchant to process fraudulent transactions and extract funds.",
            tactic=FT3Tactic.MERCHANT_FRAUD,
            severity=FT3Severity.CRITICAL,
            indicators=[
                "Merchant with no web presence or physical address",
                "High chargeback ratio within first 30 days",
                "All transactions from a single cardholder or narrow cohort",
            ],
            mitigations=[
                "Merchant underwriting and KYB verification",
                "Chargeback ratio monitoring with early termination",
                "Transaction diversity analysis",
            ],
        ),

        # ---- TA07 Promo Abuse ----
        FT3Technique(
            technique_id="T0701",
            name="Multi-Account Promo Farming",
            description="Creating multiple accounts to repeatedly exploit sign-up bonuses or promotional offers.",
            tactic=FT3Tactic.PROMO_ABUSE,
            severity=FT3Severity.MEDIUM,
            indicators=[
                "Multiple accounts sharing device fingerprint or IP",
                "Promotion redemption immediately followed by withdrawal",
                "Referral chains with no genuine activity",
            ],
            mitigations=[
                "Device fingerprint deduplication across promo claims",
                "Promo lockup periods before fund withdrawal",
                "Graph analysis on referral networks",
            ],
        ),

        # ---- TA13 Agent Impersonation (agent-specific) ----
        FT3Technique(
            technique_id="T1301",
            name="Agent Identity Spoofing",
            description="Mimicking legitimate agent credentials to authorize fraudulent transactions.",
            tactic=FT3Tactic.AGENT_IMPERSONATION,
            severity=FT3Severity.CRITICAL,
            indicators=[
                "Agent API key used from unrecognized infrastructure",
                "TAP attestation chain mismatch",
                "Agent behavior diverges from historical profile",
            ],
            mitigations=[
                "TAP Ed25519/ECDSA-P256 identity verification",
                "Infrastructure fingerprinting for agent execution environment",
                "Behavioral baselining per agent identity",
            ],
            is_agent_specific=True,
        ),
        FT3Technique(
            technique_id="T1302",
            name="Delegation Chain Forgery",
            description="Fabricating or tampering with agent delegation chains to gain unauthorized spending authority.",
            tactic=FT3Tactic.AGENT_IMPERSONATION,
            severity=FT3Severity.CRITICAL,
            indicators=[
                "Delegation chain with unknown root principal",
                "Timestamp gaps in delegation chain",
                "Delegated permissions exceed parent scope",
            ],
            mitigations=[
                "Cryptographic delegation chain verification",
                "Scope narrowing enforcement (child <= parent)",
                "Delegation chain depth limits",
            ],
            is_agent_specific=True,
        ),

        # ---- TA14 Policy Evasion (agent-specific) ----
        FT3Technique(
            technique_id="T1401",
            name="Split Transaction Evasion",
            description="Splitting a large payment into multiple smaller transactions to stay under policy limits.",
            tactic=FT3Tactic.POLICY_EVASION,
            severity=FT3Severity.HIGH,
            indicators=[
                "Multiple transactions to same merchant within short window",
                "Individual amounts just below policy threshold",
                "Aggregate exceeds what single transaction would trigger",
            ],
            mitigations=[
                "Aggregate spending analysis per agent/merchant window",
                "Sliding-window policy evaluation",
                "Structuring detection adapted for agent policies",
            ],
            is_agent_specific=True,
        ),
        FT3Technique(
            technique_id="T1402",
            name="MCC Manipulation",
            description="Misrepresenting merchant category code to bypass category-based spending policies.",
            tactic=FT3Tactic.POLICY_EVASION,
            severity=FT3Severity.HIGH,
            indicators=[
                "MCC inconsistent with merchant's known category",
                "Frequent MCC changes on same merchant",
                "Transactions in blocked MCC via relay merchant",
            ],
            mitigations=[
                "MCC verification against merchant registry",
                "Transaction enrichment with merchant intelligence",
                "Policy evaluation on enriched (not raw) MCC",
            ],
            is_agent_specific=True,
        ),
        FT3Technique(
            technique_id="T1403",
            name="Temporal Evasion",
            description="Timing transactions to exploit policy reset windows (e.g., daily/weekly limit resets).",
            tactic=FT3Tactic.POLICY_EVASION,
            severity=FT3Severity.MEDIUM,
            indicators=[
                "Transactions clustered around policy reset boundaries",
                "Spending velocity spikes at window edges",
                "Pattern of max-limit usage in consecutive windows",
            ],
            mitigations=[
                "Rolling window policies instead of fixed resets",
                "Cross-window aggregate monitoring",
                "Anomaly detection on temporal spending patterns",
            ],
            is_agent_specific=True,
        ),

        # ---- TA15 Autonomous Fraud (agent-specific) ----
        FT3Technique(
            technique_id="T1501",
            name="Prompt Injection Payment",
            description="Tricking an AI agent into making unauthorized payments via prompt injection in upstream data.",
            tactic=FT3Tactic.AUTONOMOUS_FRAUD,
            severity=FT3Severity.CRITICAL,
            indicators=[
                "Payment intent originating from untrusted data source",
                "Transaction description contains instruction-like text",
                "Agent context window shows injected payment directives",
            ],
            mitigations=[
                "Input sanitization on all agent context sources",
                "Mandate chain verification (AP2) for every payment",
                "Human-in-the-loop approval above threshold",
            ],
            is_agent_specific=True,
        ),
        FT3Technique(
            technique_id="T1502",
            name="Runaway Spending",
            description="Agent caught in a loop making repeated unauthorized transactions without human oversight.",
            tactic=FT3Tactic.AUTONOMOUS_FRAUD,
            severity=FT3Severity.HIGH,
            indicators=[
                "Rapid repeated transactions with identical parameters",
                "Exponentially growing transaction frequency",
                "No human approval events in extended spending sequence",
            ],
            mitigations=[
                "Circuit breaker on transaction velocity per agent",
                "Kill switch activation on anomalous spending loops",
                "Mandatory human checkpoint after N consecutive payments",
            ],
            is_agent_specific=True,
        ),
        FT3Technique(
            technique_id="T1503",
            name="Tool Abuse",
            description="Agent misusing payment tools beyond their intended scope or authorization.",
            tactic=FT3Tactic.AUTONOMOUS_FRAUD,
            severity=FT3Severity.HIGH,
            indicators=[
                "Tool invocations outside declared agent capabilities",
                "Payment tool used for non-payment purposes",
                "Tool parameters manipulated beyond valid ranges",
            ],
            mitigations=[
                "Strict tool schema validation",
                "Capability-scoped tool access (least privilege)",
                "Audit trail correlation of tool usage vs. mandate",
            ],
            is_agent_specific=True,
        ),
    ]


# ============ Factory & Helpers ============


def create_ft3_registry(load_defaults: bool = True) -> FT3TaxonomyRegistry:
    """Factory function to create an FT3TaxonomyRegistry.

    Args:
        load_defaults: If True (default), pre-populate with the standard
            FT3 + Sardis agent-specific techniques.
    """
    registry = FT3TaxonomyRegistry()
    if load_defaults:
        registry.load_standard_taxonomy()
    return registry


def classify_event(
    technique_id: str,
    agent_id: str = "",
    transaction_id: str = "",
    confidence: float = 0.0,
    details: dict | None = None,
) -> FT3Event:
    """Convenience function to create an FT3Event without a registry.

    Useful for lightweight classification where a full registry is not needed.
    """
    return FT3Event(
        event_id=uuid.uuid4().hex[:12],
        technique_id=technique_id,
        agent_id=agent_id,
        transaction_id=transaction_id,
        confidence=confidence,
        details=details or {},
    )
