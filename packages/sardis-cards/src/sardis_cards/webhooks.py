"""Webhook handling for card transaction events."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Optional
import hashlib
import hmac
import json
import logging

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Types of card webhook events."""
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_SETTLED = "transaction.settled"
    TRANSACTION_DECLINED = "transaction.declined"
    TRANSACTION_REVERSED = "transaction.reversed"
    CARD_CREATED = "card.created"
    CARD_ACTIVATED = "card.activated"
    CARD_FROZEN = "card.frozen"
    CARD_CANCELLED = "card.cancelled"


@dataclass
class WebhookEvent:
    """Parsed webhook event."""
    event_id: str
    event_type: WebhookEventType
    created_at: datetime
    data: dict[str, Any]
    
    # Convenience properties for transaction events
    @property
    def card_id(self) -> Optional[str]:
        return self.data.get("card_token") or self.data.get("card_id")
    
    @property
    def transaction_id(self) -> Optional[str]:
        return self.data.get("token") or self.data.get("transaction_id")
    
    @property
    def amount(self) -> Optional[Decimal]:
        amount = self.data.get("amount")
        if amount is not None:
            # Lithic sends amounts in cents
            return Decimal(str(amount)) / 100
        return None
    
    @property
    def merchant_name(self) -> Optional[str]:
        merchant = self.data.get("merchant", {})
        return merchant.get("descriptor") or merchant.get("name")


class CardWebhookHandler:
    """
    Handler for card provider webhooks.
    
    Verifies signatures and parses events from card providers.
    """
    
    def __init__(self, secret: str, provider: str = "lithic") -> None:
        """
        Initialize webhook handler.
        
        Args:
            secret: Webhook signing secret from provider
            provider: Provider name (lithic, marqeta, etc.)
        """
        self._secret = secret
        self._provider = provider
    
    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Raw request body bytes
            signature: Signature from provider header
            timestamp: Optional timestamp for replay protection
            
        Returns:
            True if signature is valid
        """
        if self._provider == "lithic":
            return self._verify_lithic_signature(payload, signature)
        elif self._provider == "marqeta":
            return self._verify_marqeta_signature(payload, signature)
        else:
            # For mock provider, always return True
            return True
    
    def _verify_lithic_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Lithic webhook signature (HMAC-SHA256)."""
        expected = hmac.new(
            self._secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    def _verify_marqeta_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Marqeta webhook signature."""
        # Marqeta uses a similar HMAC approach
        expected = hmac.new(
            self._secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    def parse_event(self, payload: bytes) -> WebhookEvent:
        """
        Parse webhook payload into an event.
        
        Args:
            payload: Raw request body bytes
            
        Returns:
            Parsed WebhookEvent
        """
        data = json.loads(payload)
        
        if self._provider == "lithic":
            return self._parse_lithic_event(data)
        elif self._provider == "marqeta":
            return self._parse_marqeta_event(data)
        else:
            return self._parse_generic_event(data)
    
    def _parse_lithic_event(self, data: dict) -> WebhookEvent:
        """Parse Lithic webhook event."""
        event_type_map = {
            "transaction.created": WebhookEventType.TRANSACTION_CREATED,
            "transaction.updated": WebhookEventType.TRANSACTION_UPDATED,
            "transaction.voided": WebhookEventType.TRANSACTION_REVERSED,
            "card.created": WebhookEventType.CARD_CREATED,
        }
        
        raw_type = data.get("type", "")
        event_type = event_type_map.get(raw_type, WebhookEventType.TRANSACTION_CREATED)
        
        return WebhookEvent(
            event_id=data.get("token", ""),
            event_type=event_type,
            created_at=datetime.now(timezone.utc),
            data=data.get("payload", data),
        )
    
    def _parse_marqeta_event(self, data: dict) -> WebhookEvent:
        """Parse Marqeta webhook event."""
        event_type_map = {
            "AUTHORIZATION": WebhookEventType.TRANSACTION_CREATED,
            "CLEARING": WebhookEventType.TRANSACTION_SETTLED,
            "REVERSAL": WebhookEventType.TRANSACTION_REVERSED,
        }
        
        raw_type = data.get("type", "")
        event_type = event_type_map.get(raw_type, WebhookEventType.TRANSACTION_CREATED)
        
        return WebhookEvent(
            event_id=data.get("token", ""),
            event_type=event_type,
            created_at=datetime.now(timezone.utc),
            data=data,
        )
    
    def _parse_generic_event(self, data: dict) -> WebhookEvent:
        """Parse generic webhook event."""
        return WebhookEvent(
            event_id=data.get("event_id", data.get("id", "")),
            event_type=WebhookEventType(data.get("type", "transaction.created")),
            created_at=datetime.now(timezone.utc),
            data=data,
        )
    
    def verify_and_parse(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> WebhookEvent:
        """
        Verify signature and parse webhook event.

        Args:
            payload: Raw request body bytes
            signature: Signature from provider header
            timestamp: Optional timestamp for replay protection

        Returns:
            Parsed WebhookEvent

        Raises:
            ValueError: If signature verification fails
        """
        if not self.verify_signature(payload, signature, timestamp):
            raise ValueError("Invalid webhook signature")

        return self.parse_event(payload)


class ASADecision(str, Enum):
    """Lithic ASA authorization decision."""
    APPROVE = "APPROVE"
    DECLINE = "DECLINE"


@dataclass
class ASARequest:
    """Parsed Lithic ASA (Authorization Stream Access) request."""
    token: str
    card_token: str
    amount_cents: int
    currency: str
    merchant_descriptor: str
    merchant_mcc: str
    merchant_id: str
    status: str
    raw_data: dict[str, Any]

    @property
    def amount(self) -> Decimal:
        return Decimal(self.amount_cents) / 100


@dataclass
class ASAResponse:
    """Response to an ASA authorization request."""
    decision: ASADecision
    reason: str
    token: str  # echo back the transaction token


class ASAHandler:
    """
    Lithic Authorization Stream Access (ASA) handler.

    Receives real-time authorization requests from Lithic and makes
    approve/decline decisions based on Sardis spending policies.

    This is a synchronous decision endpoint — Lithic waits for a
    response before approving or declining the card transaction at
    the network level.
    """

    def __init__(
        self,
        webhook_handler: CardWebhookHandler,
        card_lookup: Optional[Callable[[str], Optional[Any]]] = None,
        policy_check: Optional[Callable[[str, Decimal, str, str], tuple[bool, str]]] = None,
        redis_client: Optional[Any] = None,
    ):
        """
        Args:
            webhook_handler: Base handler for signature verification
            card_lookup: Async callable(card_token) -> Card or None
            policy_check: Async callable(wallet_id, amount, merchant_mcc, merchant_name) -> (allowed, reason)
            redis_client: Optional Redis client for persistent idempotency
        """
        self._handler = webhook_handler
        self._card_lookup = card_lookup
        self._policy_check = policy_check
        self._redis = redis_client
        self._processed: set[str] = set()

        # Blocked MCC codes (high-risk categories)
        self._blocked_mccs: set[str] = {
            # Gambling
            "7800",  # Government-owned lotteries
            "7801",  # Online casinos (government-licensed)
            "7802",  # Horse/dog racing
            "7995",  # Betting, casino gambling, lottery tickets
            # Financial instruments / quasi-cash
            "6010",  # Manual cash disbursements
            "6011",  # Automated cash disbursements (ATMs)
            "6051",  # Quasi-cash: foreign currency, money orders, crypto
            "6540",  # Stored value card purchase/load (prepaid cards)
            # High-risk services
            "5933",  # Pawn shops
            "7273",  # Dating/escort services
            # Securities (agent should not trade)
            "6211",  # Security brokers/dealers
            # Wire transfers (potential for irreversible fund movement)
            "4829",  # Wire transfers / money orders
        }

    async def _mark_processed(self, token: str) -> None:
        """Mark token as processed in memory and optionally Redis."""
        self._processed.add(token)
        if self._redis:
            try:
                await self._redis.sadd("sardis:asa:processed", token)
                await self._redis.expire("sardis:asa:processed", 86400)  # 24h TTL
            except Exception:
                pass  # In-memory set is sufficient fallback

    def add_blocked_mcc(self, mcc: str) -> None:
        """Add a merchant category code to the block list."""
        self._blocked_mccs.add(mcc)

    async def handle_authorization(
        self,
        payload: bytes,
        signature: str,
    ) -> ASAResponse:
        """
        Handle a Lithic ASA authorization request.

        Must respond quickly (< 2 seconds) or Lithic will use its
        default decision.

        Args:
            payload: Raw request body
            signature: Lithic webhook signature

        Returns:
            ASAResponse with approve/decline decision
        """
        # 1. Verify signature
        if not self._handler.verify_signature(payload, signature):
            logger.warning("ASA: Invalid webhook signature")
            return ASAResponse(
                decision=ASADecision.DECLINE,
                reason="invalid_signature",
                token="",
            )

        # 2. Parse authorization request
        data = json.loads(payload)
        asa_req = self._parse_asa_request(data)

        # 3. Idempotency check (Redis-backed if available, in-memory fallback)
        is_duplicate = asa_req.token in self._processed
        if not is_duplicate and self._redis:
            try:
                is_duplicate = await self._redis.sismember("sardis:asa:processed", asa_req.token)
            except Exception:
                pass  # Fall back to in-memory check
        if is_duplicate:
            logger.info(f"ASA: Duplicate authorization {asa_req.token}")
            return ASAResponse(
                decision=ASADecision.APPROVE,
                reason="duplicate_approved",
                token=asa_req.token,
            )

        logger.info(
            f"ASA: Authorization request token={asa_req.token} "
            f"card={asa_req.card_token} amount=${asa_req.amount} "
            f"merchant={asa_req.merchant_descriptor} mcc={asa_req.merchant_mcc}"
        )

        # 4. Check blocked MCCs
        if asa_req.merchant_mcc in self._blocked_mccs:
            logger.warning(
                f"ASA: Declined - blocked MCC {asa_req.merchant_mcc} "
                f"for card {asa_req.card_token}"
            )
            await self._mark_processed(asa_req.token)
            return ASAResponse(
                decision=ASADecision.DECLINE,
                reason=f"blocked_merchant_category_{asa_req.merchant_mcc}",
                token=asa_req.token,
            )

        # 5. Look up card and check spending limits
        if self._card_lookup:
            try:
                card = await self._card_lookup(asa_req.card_token)
                if card is None:
                    logger.warning(f"ASA: Card not found {asa_req.card_token}")
                    await self._mark_processed(asa_req.token)
                    return ASAResponse(
                        decision=ASADecision.DECLINE,
                        reason="card_not_found",
                        token=asa_req.token,
                    )

                can_authorize, card_reason = card.can_authorize(
                    asa_req.amount,
                    merchant_id=asa_req.merchant_id,
                )
                if not can_authorize:
                    logger.info(f"ASA: Declined by card limits - {card_reason}")
                    await self._mark_processed(asa_req.token)
                    return ASAResponse(
                        decision=ASADecision.DECLINE,
                        reason=card_reason,
                        token=asa_req.token,
                    )
            except Exception as e:
                logger.error(f"ASA: Card lookup failed: {e}")
                # Fail-open for card lookup errors to avoid blocking all transactions
                # The card-level limits at Lithic will still apply

        # 6. Check spending policy (if configured)
        if self._policy_check:
            try:
                allowed, policy_reason = await self._policy_check(
                    asa_req.card_token,
                    asa_req.amount,
                    asa_req.merchant_mcc,
                    asa_req.merchant_descriptor,
                )
                if not allowed:
                    logger.info(f"ASA: Declined by policy - {policy_reason}")
                    await self._mark_processed(asa_req.token)
                    return ASAResponse(
                        decision=ASADecision.DECLINE,
                        reason=policy_reason,
                        token=asa_req.token,
                    )
            except Exception as e:
                logger.error(f"ASA: Policy check failed: {e}")
                # Fail-closed on policy errors — decline if policy engine is down
                await self._mark_processed(asa_req.token)
                return ASAResponse(
                    decision=ASADecision.DECLINE,
                    reason="policy_check_failed",
                    token=asa_req.token,
                )

        # 7. Approved
        await self._mark_processed(asa_req.token)
        logger.info(f"ASA: Approved token={asa_req.token} amount=${asa_req.amount}")
        return ASAResponse(
            decision=ASADecision.APPROVE,
            reason="approved",
            token=asa_req.token,
        )

    def _parse_asa_request(self, data: dict) -> ASARequest:
        """Parse Lithic ASA webhook payload."""
        payload = data.get("payload", data)
        merchant = payload.get("merchant", {})
        return ASARequest(
            token=payload.get("token", ""),
            card_token=payload.get("card_token", payload.get("card", {}).get("token", "")),
            amount_cents=abs(payload.get("amount", 0)),
            currency=merchant.get("currency", "USD"),
            merchant_descriptor=merchant.get("descriptor", ""),
            merchant_mcc=merchant.get("mcc", ""),
            merchant_id=merchant.get("acceptor_id", ""),
            status=payload.get("status", ""),
            raw_data=data,
        )

    def clear_processed(self, max_size: int = 10000) -> None:
        """Prevent unbounded memory growth."""
        if len(self._processed) > max_size:
            self._processed.clear()


class AutoConversionWebhookHandler:
    """
    Webhook handler that integrates with auto-conversion service.

    Automatically triggers USDC → USD conversion when card
    transactions are authorized.
    """

    def __init__(
        self,
        webhook_handler: CardWebhookHandler,
        card_to_wallet_map: dict[str, str],
        on_conversion_needed: Optional[Callable[[str, int, str], None]] = None,
        redis_client: Optional[Any] = None,
    ):
        """
        Initialize auto-conversion webhook handler.

        Args:
            webhook_handler: Base webhook handler for signature verification
            card_to_wallet_map: Mapping of card_id -> wallet_id
            on_conversion_needed: Callback when conversion is needed.
                Args: (wallet_id, amount_cents, card_transaction_id)
            redis_client: Optional Redis client for persistent idempotency
        """
        self._handler = webhook_handler
        self._card_wallet_map = card_to_wallet_map
        self._on_conversion_needed = on_conversion_needed
        self._redis = redis_client
        self._processed_events: set[str] = set()

    def register_card(self, card_id: str, wallet_id: str) -> None:
        """Register a card to wallet mapping."""
        self._card_wallet_map[card_id] = wallet_id
        logger.info(f"Registered card {card_id} for auto-conversion")

    def unregister_card(self, card_id: str) -> None:
        """Remove card from auto-conversion."""
        if card_id in self._card_wallet_map:
            del self._card_wallet_map[card_id]

    async def process_webhook(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Process webhook and trigger auto-conversion if needed.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature
            timestamp: Optional timestamp

        Returns:
            Dictionary with processing result, or None if event skipped
        """
        # Verify and parse event
        event = self._handler.verify_and_parse(payload, signature, timestamp)

        # Skip if already processed (idempotency - Redis-backed if available)
        is_duplicate = event.event_id in self._processed_events
        if not is_duplicate and self._redis:
            try:
                is_duplicate = await self._redis.sismember(
                    "sardis:webhook:processed", event.event_id
                )
            except Exception:
                pass
        if is_duplicate:
            logger.info(f"Skipping already processed event: {event.event_id}")
            return None

        self._processed_events.add(event.event_id)
        if self._redis:
            try:
                await self._redis.sadd("sardis:webhook:processed", event.event_id)
                await self._redis.expire("sardis:webhook:processed", 86400)
            except Exception:
                pass

        # Only process transaction created events (authorizations)
        if event.event_type != WebhookEventType.TRANSACTION_CREATED:
            logger.debug(f"Skipping non-authorization event: {event.event_type}")
            return {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "action": "skipped",
                "reason": "not_authorization",
            }

        # Check if this card is registered for auto-conversion
        card_id = event.card_id
        if not card_id or card_id not in self._card_wallet_map:
            logger.debug(f"Card not registered for auto-conversion: {card_id}")
            return {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "action": "skipped",
                "reason": "card_not_registered",
            }

        wallet_id = self._card_wallet_map[card_id]
        amount = event.amount

        if amount is None or amount <= 0:
            logger.warning(f"Invalid amount in webhook: {amount}")
            return {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "action": "skipped",
                "reason": "invalid_amount",
            }

        # Convert Decimal to cents
        amount_cents = int(amount * 100)

        logger.info(
            f"Card authorization detected - triggering auto-conversion: "
            f"card={card_id}, wallet={wallet_id}, amount=${amount_cents / 100:.2f}, "
            f"merchant={event.merchant_name}"
        )

        # Trigger conversion callback
        if self._on_conversion_needed:
            self._on_conversion_needed(wallet_id, amount_cents, event.transaction_id or "")

        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "action": "conversion_triggered",
            "wallet_id": wallet_id,
            "card_id": card_id,
            "amount_cents": amount_cents,
            "merchant": event.merchant_name,
            "transaction_id": event.transaction_id,
        }

    def clear_processed_events(self, older_than_count: int = 1000) -> None:
        """Clear old processed events to prevent memory growth."""
        if len(self._processed_events) > older_than_count * 2:
            # Keep only the most recent events (simple approach)
            self._processed_events.clear()
            logger.info("Cleared processed events cache")
