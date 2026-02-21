"""Input validation for payment parameters.

Validates addresses, amounts, token/chain combinations, and sanitizes inputs.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Set

from pydantic import BaseModel, field_validator


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


class WalletAddressValidator:
    """Validator for blockchain wallet addresses."""

    # Ethereum address pattern (0x + 40 hex chars)
    ETH_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")

    @staticmethod
    def validate_ethereum_address(address: str, check_checksum: bool = True) -> str:
        """Validate an Ethereum address.

        Args:
            address: Address to validate
            check_checksum: Whether to validate EIP-55 checksum

        Returns:
            Validated address

        Raises:
            ValidationError: If address is invalid
        """
        if not address:
            raise ValidationError("Address cannot be empty")

        # Check basic format
        if not WalletAddressValidator.ETH_ADDRESS_PATTERN.match(address):
            raise ValidationError(
                f"Invalid Ethereum address format: {address}. "
                "Must be 0x followed by 40 hexadecimal characters."
            )

        # Validate checksum if required
        if check_checksum and address != address.lower() and address != address.upper():
            if not WalletAddressValidator._verify_checksum(address):
                raise ValidationError(
                    f"Invalid EIP-55 checksum for address: {address}. "
                    "Address checksum does not match."
                )

        return address

    @staticmethod
    def _verify_checksum(address: str) -> bool:
        """Verify EIP-55 checksum.

        Args:
            address: Address to verify

        Returns:
            True if checksum is valid
        """
        try:
            import hashlib

            # Remove 0x prefix
            address_no_prefix = address[2:]

            # Hash the lowercase address
            address_hash = hashlib.sha3_256(address_no_prefix.lower().encode()).hexdigest()

            # Check each character
            for i, char in enumerate(address_no_prefix):
                if char in "0123456789":
                    continue

                hash_char = int(address_hash[i], 16)

                if hash_char >= 8:
                    if char.upper() != char:
                        return False
                else:
                    if char.lower() != char:
                        return False

            return True
        except Exception:
            return False


class AmountValidator:
    """Validator for payment amounts."""

    # Maximum supported decimal places for different tokens
    TOKEN_DECIMALS = {
        "USDC": 6,
        "USDT": 6,
        "EURC": 6,
        "PYUSD": 6,
        "DAI": 18,
    }

    @staticmethod
    def validate_amount(
        amount: Decimal | str | float | int,
        token: str,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
    ) -> Decimal:
        """Validate a payment amount.

        Args:
            amount: Amount to validate
            token: Token symbol (e.g., "USDC")
            min_amount: Optional minimum amount
            max_amount: Optional maximum amount

        Returns:
            Validated amount as Decimal

        Raises:
            ValidationError: If amount is invalid
        """
        # Convert to Decimal
        try:
            if isinstance(amount, Decimal):
                decimal_amount = amount
            elif isinstance(amount, str):
                decimal_amount = Decimal(amount)
            elif isinstance(amount, (int, float)):
                decimal_amount = Decimal(str(amount))
            else:
                raise ValidationError(f"Invalid amount type: {type(amount)}")
        except (InvalidOperation, ValueError) as e:
            raise ValidationError(f"Invalid amount format: {amount}. Error: {e}")

        # Check positive
        if decimal_amount <= 0:
            raise ValidationError(f"Amount must be positive. Got: {decimal_amount}")

        # Check decimal precision
        max_decimals = AmountValidator.TOKEN_DECIMALS.get(token.upper(), 18)
        amount_str = str(decimal_amount)

        if "." in amount_str:
            decimal_places = len(amount_str.split(".")[1])
            if decimal_places > max_decimals:
                raise ValidationError(
                    f"Amount has too many decimal places for {token}. "
                    f"Maximum: {max_decimals}, got: {decimal_places}"
                )

        # Check bounds
        if min_amount is not None and decimal_amount < min_amount:
            raise ValidationError(
                f"Amount below minimum. Minimum: {min_amount}, got: {decimal_amount}"
            )

        if max_amount is not None and decimal_amount > max_amount:
            raise ValidationError(
                f"Amount exceeds maximum. Maximum: {max_amount}, got: {decimal_amount}"
            )

        return decimal_amount


class ChainTokenValidator:
    """Validator for chain and token combinations."""

    # Supported token/chain combinations
    SUPPORTED_COMBINATIONS: Set[tuple[str, str]] = {
        ("BASE", "USDC"),
        ("BASE", "EURC"),
        ("POLYGON", "USDC"),
        ("POLYGON", "USDT"),
        ("POLYGON", "EURC"),
        ("ETHEREUM", "USDC"),
        ("ETHEREUM", "USDT"),
        ("ETHEREUM", "PYUSD"),
        ("ETHEREUM", "EURC"),
        ("ARBITRUM", "USDC"),
        ("ARBITRUM", "USDT"),
        ("OPTIMISM", "USDC"),
        ("OPTIMISM", "USDT"),
    }

    @staticmethod
    def validate_combination(chain: str, token: str) -> tuple[str, str]:
        """Validate that a chain/token combination is supported.

        Args:
            chain: Chain name (e.g., "BASE", "ETHEREUM")
            token: Token symbol (e.g., "USDC")

        Returns:
            Normalized (chain, token) tuple

        Raises:
            ValidationError: If combination is not supported
        """
        chain_upper = chain.upper()
        token_upper = token.upper()

        if (chain_upper, token_upper) not in ChainTokenValidator.SUPPORTED_COMBINATIONS:
            raise ValidationError(
                f"Unsupported chain/token combination: {chain}/{token}. "
                f"Supported combinations: {ChainTokenValidator.SUPPORTED_COMBINATIONS}"
            )

        return (chain_upper, token_upper)


class StringSanitizer:
    """Sanitizer for string inputs to prevent injection attacks."""

    # Dangerous patterns to block
    SQL_INJECTION_PATTERN = re.compile(
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)|--|;|/\*|\*/|xp_|sp_",
        re.IGNORECASE,
    )

    SCRIPT_INJECTION_PATTERN = re.compile(
        r"<script|javascript:|onerror=|onload=|eval\(|expression\(",
        re.IGNORECASE,
    )

    @staticmethod
    def sanitize_merchant_name(name: str, max_length: int = 100) -> str:
        """Sanitize merchant name.

        Args:
            name: Merchant name to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized name

        Raises:
            ValidationError: If name contains dangerous patterns
        """
        if not name or not name.strip():
            raise ValidationError("Merchant name cannot be empty")

        name = name.strip()

        # Check length
        if len(name) > max_length:
            raise ValidationError(
                f"Merchant name too long. Maximum: {max_length}, got: {len(name)}"
            )

        # Check for injection patterns
        if StringSanitizer.SQL_INJECTION_PATTERN.search(name):
            raise ValidationError("Merchant name contains potentially dangerous SQL patterns")

        if StringSanitizer.SCRIPT_INJECTION_PATTERN.search(name):
            raise ValidationError("Merchant name contains potentially dangerous script patterns")

        return name

    @staticmethod
    def sanitize_purpose(purpose: str, max_length: int = 500) -> str:
        """Sanitize payment purpose/description.

        Args:
            purpose: Purpose to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized purpose

        Raises:
            ValidationError: If purpose contains dangerous patterns
        """
        if not purpose or not purpose.strip():
            raise ValidationError("Payment purpose cannot be empty")

        purpose = purpose.strip()

        # Check length
        if len(purpose) > max_length:
            raise ValidationError(
                f"Payment purpose too long. Maximum: {max_length}, got: {len(purpose)}"
            )

        # Check for injection patterns
        if StringSanitizer.SQL_INJECTION_PATTERN.search(purpose):
            raise ValidationError("Payment purpose contains potentially dangerous SQL patterns")

        if StringSanitizer.SCRIPT_INJECTION_PATTERN.search(purpose):
            raise ValidationError("Payment purpose contains potentially dangerous script patterns")

        return purpose


class PaymentInputValidator(BaseModel):
    """Comprehensive payment input validator using Pydantic."""

    recipient_address: str
    amount: Decimal
    token: str
    chain: str
    merchant_name: str | None = None
    purpose: str | None = None

    @field_validator("recipient_address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate recipient address."""
        return WalletAddressValidator.validate_ethereum_address(v)

    @field_validator("amount")
    @classmethod
    def validate_amount_positive(cls, v: Decimal) -> Decimal:
        """Validate amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("merchant_name")
    @classmethod
    def validate_merchant(cls, v: str | None) -> str | None:
        """Validate and sanitize merchant name."""
        if v is None:
            return None
        return StringSanitizer.sanitize_merchant_name(v)

    @field_validator("purpose")
    @classmethod
    def validate_purpose_field(cls, v: str | None) -> str | None:
        """Validate and sanitize purpose."""
        if v is None:
            return None
        return StringSanitizer.sanitize_purpose(v)

    def validate_full(self) -> None:
        """Run full validation including cross-field checks.

        Raises:
            ValidationError: If validation fails
        """
        # Validate amount with token-specific rules
        AmountValidator.validate_amount(self.amount, self.token)

        # Validate chain/token combination
        ChainTokenValidator.validate_combination(self.chain, self.token)
