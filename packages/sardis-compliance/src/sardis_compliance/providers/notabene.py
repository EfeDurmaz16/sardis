"""Notabene Travel Rule provider.

Integrates Notabene's Transact API for FATF Recommendation 16 compliance.
Handles VASP-to-VASP transfer notifications, counterparty discovery,
PII encryption via SafePII, and transfer lifecycle management.

API Reference: https://devx.notabene.id/
Issue: #139
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx

from sardis_compliance.travel_rule import (
    BeneficiaryInfo,
    OriginatorInfo,
    TravelRuleProvider,
    TravelRuleStatus,
    TravelRuleTransfer,
    VASPProtocol,
)

logger = logging.getLogger(__name__)

# Notabene API base URLs
NOTABENE_API_URLS = {
    "production": "https://api.notabene.id",
    "sandbox": "https://api.notabene.dev",
}

DEFAULT_ENVIRONMENT = "sandbox"


class NotabeneTransferStatus(str, Enum):
    """Notabene transfer lifecycle statuses."""
    INITIATED = "INITIATED"
    PENDING_BENEFICIARY = "PENDING_BENEFICIARY_CONFIRMATION"
    PENDING_ORIGINATOR = "PENDING_ORIGINATOR_AUTHORIZATION"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"


class AddressType(str, Enum):
    """Blockchain address ownership type."""
    HOSTED = "HOSTED"
    UNHOSTED = "UNHOSTED"
    UNKNOWN = "UNKNOWN"


class ValidationType(str, Enum):
    """Transfer validation result type."""
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    TRAVELRULE = "TRAVELRULE"
    NON_CUSTODIAL = "NON_CUSTODIAL"


class SafePIIMode(str, Enum):
    """PII encryption mode."""
    HOSTED = "hosted"
    END_TO_END = "e2e"
    HYBRID = "hybrid"


@dataclass
class ValidationResult:
    """Result from Notabene's pre-transaction validation API."""
    is_valid: bool
    transfer_type: ValidationType = ValidationType.TRAVELRULE
    beneficiary_address_type: AddressType = AddressType.UNKNOWN
    beneficiary_vasp_did: str | None = None
    beneficiary_vasp_name: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class NotabeneTransfer:
    """Notabene transfer record with full lifecycle tracking."""
    notabene_id: str | None = None
    local_transfer_id: str = ""
    status: NotabeneTransferStatus = NotabeneTransferStatus.INITIATED
    originator_vasp_did: str = ""
    beneficiary_vasp_did: str | None = None
    originator_did: str = ""
    beneficiary_did: str = ""
    asset: str = ""
    amount: str = ""
    blockchain: str = ""
    origin_address: str = ""
    destination_address: str = ""
    transaction_ref: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


# Asset mapping: Sardis token names → Notabene asset identifiers
ASSET_MAP: dict[str, str] = {
    "USDC": "USDC",
    "USDT": "USDT",
    "EURC": "EURC",
    "ETH": "ETH",
    "PYUSD": "PYUSD",
}

# Chain mapping: Sardis chain names → Notabene blockchain identifiers
CHAIN_MAP: dict[str, str] = {
    "ethereum": "ETH",
    "base": "BASE",
    "polygon": "MATIC",
    "arbitrum": "ARB",
    "optimism": "OP",
    "arc": "ETH",  # Circle L1 uses ETH identifiers
}


class NotabeneError(Exception):
    """Error from Notabene API or configuration."""
    pass


def _status_to_travel_rule(status: NotabeneTransferStatus) -> TravelRuleStatus:
    """Map Notabene transfer status to TravelRuleStatus."""
    mapping: dict[NotabeneTransferStatus, TravelRuleStatus] = {
        NotabeneTransferStatus.INITIATED: TravelRuleStatus.SENT,
        NotabeneTransferStatus.PENDING_BENEFICIARY: TravelRuleStatus.SENT,
        NotabeneTransferStatus.PENDING_ORIGINATOR: TravelRuleStatus.RECEIVED,
        NotabeneTransferStatus.AUTHORIZED: TravelRuleStatus.CONFIRMED,
        NotabeneTransferStatus.REJECTED: TravelRuleStatus.REJECTED,
        NotabeneTransferStatus.CANCELLED: TravelRuleStatus.REJECTED,
        NotabeneTransferStatus.SETTLED: TravelRuleStatus.CONFIRMED,
        NotabeneTransferStatus.FAILED: TravelRuleStatus.REJECTED,
        NotabeneTransferStatus.INCOMPLETE: TravelRuleStatus.PENDING,
    }
    return mapping.get(status, TravelRuleStatus.PENDING)


def _build_originator_ivms(originator: OriginatorInfo) -> dict[str, Any]:
    """Build IVMS 101 originator payload from OriginatorInfo."""
    person: dict[str, Any] = {}

    if originator.name:
        # Split name into parts (best effort)
        parts = originator.name.strip().split()
        if len(parts) >= 2:
            person["naturalPerson"] = {
                "name": {
                    "nameIdentifier": [{
                        "primaryIdentifier": parts[-1],
                        "secondaryIdentifier": " ".join(parts[:-1]),
                        "nameIdentifierType": "LEGL",
                    }]
                }
            }
        else:
            person["naturalPerson"] = {
                "name": {
                    "nameIdentifier": [{
                        "primaryIdentifier": originator.name,
                        "nameIdentifierType": "LEGL",
                    }]
                }
            }

    if originator.country:
        person.setdefault("naturalPerson", {})["geographicAddress"] = [{
            "country": originator.country,
            "addressType": "GEOG",
        }]

    if originator.date_of_birth:
        person.setdefault("naturalPerson", {})["dateOfBirth"] = originator.date_of_birth

    if originator.national_id:
        person.setdefault("naturalPerson", {})["nationalIdentification"] = {
            "nationalIdentifier": originator.national_id,
            "nationalIdentifierType": "MISC",
        }

    return person


def _build_beneficiary_ivms(beneficiary: BeneficiaryInfo) -> dict[str, Any]:
    """Build IVMS 101 beneficiary payload from BeneficiaryInfo."""
    person: dict[str, Any] = {}

    if beneficiary.name:
        parts = beneficiary.name.strip().split()
        if len(parts) >= 2:
            person["naturalPerson"] = {
                "name": {
                    "nameIdentifier": [{
                        "primaryIdentifier": parts[-1],
                        "secondaryIdentifier": " ".join(parts[:-1]),
                        "nameIdentifierType": "LEGL",
                    }]
                }
            }
        else:
            person["naturalPerson"] = {
                "name": {
                    "nameIdentifier": [{
                        "primaryIdentifier": beneficiary.name,
                        "nameIdentifierType": "LEGL",
                    }]
                }
            }

    if beneficiary.country:
        person.setdefault("naturalPerson", {})["geographicAddress"] = [{
            "country": beneficiary.country,
            "addressType": "GEOG",
        }]

    return person


class NotabeneTravelRuleProvider(TravelRuleProvider):
    """Notabene Travel Rule provider.

    Integrates Notabene's Transact API for automated VASP-to-VASP
    Travel Rule compliance. Handles:
    - Pre-transaction validation (threshold + counterparty discovery)
    - Transfer creation with IVMS 101 data
    - Transfer lifecycle monitoring
    - PII encryption via SafePII (hosted mode by default)

    Configuration via environment variables:
        NOTABENE_AUTH_TOKEN     — Bearer token for API authentication
        NOTABENE_VASP_DID       — Your VASP's DID identifier
        NOTABENE_ENVIRONMENT    — "production" or "sandbox" (default: sandbox)
        NOTABENE_WEBHOOK_SECRET — HMAC secret for webhook signature verification

    Usage:
        provider = NotabeneTravelRuleProvider()
        # Validate before sending
        validation = await provider.validate_transfer(transfer)
        if validation.transfer_type == ValidationType.TRAVELRULE:
            status = await provider.send_transfer_info(transfer)
    """

    def __init__(
        self,
        auth_token: str | None = None,
        vasp_did: str | None = None,
        environment: str | None = None,
        webhook_secret: str | None = None,
        pii_mode: SafePIIMode = SafePIIMode.HOSTED,
        timeout: float = 15.0,
    ) -> None:
        self._auth_token = auth_token or os.getenv("NOTABENE_AUTH_TOKEN", "")
        self._vasp_did = vasp_did or os.getenv("NOTABENE_VASP_DID", "")
        env = environment or os.getenv("NOTABENE_ENVIRONMENT", DEFAULT_ENVIRONMENT)
        self._base_url = NOTABENE_API_URLS.get(env, NOTABENE_API_URLS[DEFAULT_ENVIRONMENT])
        self._webhook_secret = webhook_secret or os.getenv("NOTABENE_WEBHOOK_SECRET", "")
        self._pii_mode = pii_mode
        self._timeout = timeout
        # In-memory transfer tracking (keyed by local transfer_id)
        self._transfers: dict[str, NotabeneTransfer] = {}

    @property
    def is_configured(self) -> bool:
        """Whether the provider has valid API credentials."""
        return bool(self._auth_token and self._vasp_did)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def validate_transfer(
        self,
        transfer: TravelRuleTransfer,
    ) -> ValidationResult:
        """Pre-transaction validation via Notabene Validation API.

        Checks threshold, identifies counterparty VASP, and returns
        required data fields. Should be called before send_transfer_info.

        Args:
            transfer: The transfer to validate.

        Returns:
            ValidationResult with counterparty info and required fields.

        Raises:
            NotabeneError: On API errors or missing configuration.
        """
        if not self.is_configured:
            raise NotabeneError("Notabene provider not configured")

        chain = CHAIN_MAP.get(transfer.chain or "", "ETH")
        asset = ASSET_MAP.get(transfer.currency, transfer.currency)

        payload: dict[str, Any] = {
            "transactionAsset": asset,
            "transactionAmount": str(transfer.amount),
            "originatorVASPdid": self._vasp_did,
            "originatorEqualsBeneficiary": False,
            "transactionBlockchainInfo": {
                "origin": transfer.originator.account_id if transfer.originator else "",
                "destination": transfer.beneficiary.account_id if transfer.beneficiary else "",
            },
        }

        if transfer.beneficiary and transfer.beneficiary.account_id:
            payload["beneficiaryRef"] = transfer.beneficiary.account_id

        if transfer.originator and transfer.originator.account_id:
            payload["originatorRef"] = transfer.originator.account_id

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/tf/validate",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise NotabeneError(
                f"Notabene validation error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise NotabeneError(f"Notabene validation request failed: {e}") from e

        # Parse validation response
        try:
            transfer_type = ValidationType(data.get("type", "TRAVELRULE"))
        except ValueError:
            transfer_type = ValidationType.TRAVELRULE

        try:
            addr_type = AddressType(data.get("beneficiaryAddressType", "UNKNOWN"))
        except ValueError:
            addr_type = AddressType.UNKNOWN

        return ValidationResult(
            is_valid=data.get("isValid", False),
            transfer_type=transfer_type,
            beneficiary_address_type=addr_type,
            beneficiary_vasp_did=data.get("beneficiaryVASPdid"),
            beneficiary_vasp_name=data.get("beneficiaryVASPname"),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            raw_response=data,
        )

    async def send_transfer_info(
        self,
        transfer: TravelRuleTransfer,
    ) -> TravelRuleStatus:
        """Create a Travel Rule transfer via Notabene Transact API.

        Sends originator/beneficiary information to the counterparty VASP
        through Notabene's protocol-agnostic messaging layer.

        Args:
            transfer: The transfer with originator/beneficiary data.

        Returns:
            TravelRuleStatus indicating the transfer state.

        Raises:
            NotabeneError: On API errors or missing configuration.
        """
        if not self.is_configured:
            raise NotabeneError("Notabene provider not configured")

        chain = CHAIN_MAP.get(transfer.chain or "", "ETH")
        asset = ASSET_MAP.get(transfer.currency, transfer.currency)

        # Build IVMS 101 payload
        originator_data = _build_originator_ivms(transfer.originator) if transfer.originator else {}
        beneficiary_data = _build_beneficiary_ivms(transfer.beneficiary) if transfer.beneficiary else {}

        payload: dict[str, Any] = {
            "transactionAsset": asset,
            "transactionAmount": str(transfer.amount),
            "originatorVASPdid": self._vasp_did,
            "originator": originator_data,
            "beneficiary": beneficiary_data,
            "transactionBlockchainInfo": {
                "origin": transfer.originator.account_id if transfer.originator else "",
                "destination": transfer.beneficiary.account_id if transfer.beneficiary else "",
            },
            "transactionRef": transfer.transfer_id,
        }

        # Add beneficiary VASP DID if known (from prior validation)
        if transfer.beneficiary and transfer.beneficiary.vasp_id:
            payload["beneficiaryVASPdid"] = transfer.beneficiary.vasp_id

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/tf/entity/{self._vasp_did}/tx",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise NotabeneError(
                f"Notabene transfer creation error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise NotabeneError(f"Notabene transfer request failed: {e}") from e

        # Parse response and track transfer
        try:
            nb_status = NotabeneTransferStatus(data.get("status", "INITIATED"))
        except ValueError:
            nb_status = NotabeneTransferStatus.INITIATED

        nb_transfer = NotabeneTransfer(
            notabene_id=data.get("id"),
            local_transfer_id=transfer.transfer_id,
            status=nb_status,
            originator_vasp_did=self._vasp_did,
            beneficiary_vasp_did=data.get("beneficiaryVASPdid"),
            asset=asset,
            amount=str(transfer.amount),
            blockchain=chain,
            origin_address=transfer.originator.account_id if transfer.originator else "",
            destination_address=transfer.beneficiary.account_id if transfer.beneficiary else "",
            transaction_ref=transfer.transfer_id,
            raw_response=data,
        )
        self._transfers[transfer.transfer_id] = nb_transfer

        logger.info(
            "Notabene transfer created: %s → %s (status=%s)",
            transfer.transfer_id,
            nb_transfer.notabene_id,
            nb_status.value,
        )

        return _status_to_travel_rule(nb_status)

    async def check_transfer_status(
        self,
        transfer_id: str,
    ) -> TravelRuleStatus:
        """Check the current status of a Travel Rule transfer.

        Args:
            transfer_id: The local transfer ID.

        Returns:
            Current TravelRuleStatus.

        Raises:
            NotabeneError: On API errors or missing configuration.
        """
        if not self.is_configured:
            raise NotabeneError("Notabene provider not configured")

        nb_transfer = self._transfers.get(transfer_id)
        if not nb_transfer or not nb_transfer.notabene_id:
            return TravelRuleStatus.PENDING

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._base_url}/tf/entity/{self._vasp_did}/tx/{nb_transfer.notabene_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise NotabeneError(
                f"Notabene status check error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise NotabeneError(f"Notabene status check failed: {e}") from e

        try:
            nb_status = NotabeneTransferStatus(data.get("status", "INITIATED"))
        except ValueError:
            nb_status = NotabeneTransferStatus.INITIATED

        nb_transfer.status = nb_status
        nb_transfer.updated_at = datetime.now(UTC)
        nb_transfer.raw_response = data

        return _status_to_travel_rule(nb_status)

    async def discover_counterparty(
        self,
        blockchain_address: str,
        blockchain: str = "ETH",
    ) -> dict[str, Any]:
        """Discover counterparty VASP for a blockchain address.

        Uses Notabene's address resolution to identify if an address
        belongs to a registered VASP.

        Args:
            blockchain_address: The destination blockchain address.
            blockchain: Blockchain identifier (e.g., "ETH", "BASE").

        Returns:
            Dict with counterparty VASP info (did, name, addressType).
        """
        if not self.is_configured:
            raise NotabeneError("Notabene provider not configured")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._base_url}/tf/simple/address/{blockchain}/{blockchain_address}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            raise NotabeneError(
                f"Notabene counterparty discovery error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise NotabeneError(f"Notabene discovery request failed: {e}") from e

    async def get_vasp_info(self, vasp_did: str) -> dict[str, Any]:
        """Fetch VASP directory entry by DID.

        Args:
            vasp_did: The VASP's DID identifier.

        Returns:
            Dict with VASP metadata (name, endpoints, pii_didkey, etc.).
        """
        if not self.is_configured:
            raise NotabeneError("Notabene provider not configured")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._base_url}/tf/simple/vasps/{vasp_did}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            raise NotabeneError(
                f"Notabene VASP lookup error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise NotabeneError(f"Notabene VASP lookup failed: {e}") from e

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        msg_id: str | None = None,
        timestamp: str | None = None,
    ) -> bool:
        """Verify a Notabene webhook signature (SVIX-based).

        Args:
            payload: Raw request body bytes.
            signature: The webhook-signature header value.
            msg_id: The webhook-id header value.
            timestamp: The webhook-timestamp header value.

        Returns:
            True if signature is valid.
        """
        if not self._webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return False

        if not timestamp:
            return False

        # SVIX signature: v1,<base64_hmac>
        signed_content = f"{msg_id}.{timestamp}.".encode() + payload
        expected = hmac.new(
            self._webhook_secret.encode(),
            signed_content,
            hashlib.sha256,
        ).hexdigest()

        # Compare against provided signatures (may be multiple)
        for sig_part in signature.split():
            if sig_part.startswith("v1,"):
                provided = sig_part[3:]
                if hmac.compare_digest(expected, provided):
                    return True

        return False

    def process_webhook_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> TravelRuleStatus | None:
        """Process a Notabene webhook event and update local state.

        Args:
            event_type: The webhook event type string.
            data: The event payload.

        Returns:
            Updated TravelRuleStatus if a tracked transfer was updated, else None.
        """
        if event_type not in (
            "notification.transactionUpdated",
            "notification.processBlockchainTransaction",
            "notification.haltBlockchainTransaction",
        ):
            return None

        tx_data = data.get("transaction", data)
        tx_ref = tx_data.get("transactionRef", "")

        nb_transfer = self._transfers.get(tx_ref)
        if not nb_transfer:
            logger.debug("Webhook for unknown transfer ref: %s", tx_ref)
            return None

        try:
            nb_status = NotabeneTransferStatus(tx_data.get("status", "INITIATED"))
        except ValueError:
            nb_status = NotabeneTransferStatus.INITIATED

        nb_transfer.status = nb_status
        nb_transfer.updated_at = datetime.now(UTC)
        nb_transfer.raw_response = tx_data

        travel_status = _status_to_travel_rule(nb_status)

        logger.info(
            "Notabene webhook: transfer %s → %s (%s)",
            tx_ref,
            nb_status.value,
            travel_status.value,
        )

        return travel_status

    async def health_check(self) -> bool:
        """Check if the Notabene API is reachable."""
        if not self.is_configured:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._base_url}/tf/simple/vasps",
                    headers=self._headers(),
                    params={"limit": 1},
                )
                return resp.status_code in (200, 401, 403)
        except Exception:
            return False
