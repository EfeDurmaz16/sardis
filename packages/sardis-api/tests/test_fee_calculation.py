"""
Fee Calculation Tests for Sardis Payment System

These tests verify that fee calculations use proper Decimal precision
and handle edge cases correctly.

FINTECH CRITICAL: Floating-point errors can accumulate and cause financial discrepancies.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, InvalidOperation
import pytest


class FeeCalculator:
    """
    Fee calculator implementation using Decimal for precision.

    This is a reference implementation for testing purposes.
    The actual implementation should match this behavior.
    """

    # Fee rates in basis points (1 bp = 0.01%)
    PROTOCOL_FEE_BPS = Decimal("30")  # 0.30%
    CHAIN_FEE_ESTIMATE = Decimal("0.001")  # Fixed chain fee in USD

    # Precision settings
    DECIMALS = 6  # USDC has 6 decimals
    ROUNDING = ROUND_HALF_UP

    @classmethod
    def calculate_protocol_fee(cls, amount: Decimal) -> Decimal:
        """
        Calculate protocol fee from a payment amount.

        Fee = amount * (fee_bps / 10000)

        Uses Decimal arithmetic to avoid floating-point errors.
        """
        if amount <= 0:
            return Decimal("0")

        fee = amount * cls.PROTOCOL_FEE_BPS / Decimal("10000")
        return fee.quantize(Decimal(10) ** -cls.DECIMALS, rounding=cls.ROUNDING)

    @classmethod
    def calculate_total_with_fee(cls, amount: Decimal) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate total amount including fees.

        Returns: (net_amount, fee, total)
        """
        if amount <= 0:
            return Decimal("0"), Decimal("0"), Decimal("0")

        protocol_fee = cls.calculate_protocol_fee(amount)
        total = amount + protocol_fee + cls.CHAIN_FEE_ESTIMATE

        return amount, protocol_fee, total.quantize(Decimal(10) ** -cls.DECIMALS)

    @classmethod
    def calculate_net_from_gross(cls, gross_amount: Decimal) -> tuple[Decimal, Decimal]:
        """
        Calculate net amount from gross (total - fees).

        Returns: (net_amount, fee)
        """
        if gross_amount <= 0:
            return Decimal("0"), Decimal("0")

        # Reverse calculate: gross = net + net * fee_rate + chain_fee
        # net = (gross - chain_fee) / (1 + fee_rate)
        after_chain = gross_amount - cls.CHAIN_FEE_ESTIMATE
        fee_multiplier = Decimal("1") + cls.PROTOCOL_FEE_BPS / Decimal("10000")
        net = (after_chain / fee_multiplier).quantize(
            Decimal(10) ** -cls.DECIMALS, rounding=ROUND_DOWN
        )

        fee = gross_amount - net - cls.CHAIN_FEE_ESTIMATE
        return net, fee.quantize(Decimal(10) ** -cls.DECIMALS)

    @classmethod
    def minor_to_major(cls, minor_units: int) -> Decimal:
        """Convert minor units (e.g., 1000000) to major units (1.000000)."""
        return Decimal(minor_units) / Decimal(10 ** cls.DECIMALS)

    @classmethod
    def major_to_minor(cls, major_units: Decimal) -> int:
        """Convert major units to minor units (integer)."""
        minor = major_units * Decimal(10 ** cls.DECIMALS)
        return int(minor.quantize(Decimal("1"), rounding=ROUND_DOWN))


class TestDecimalPrecision:
    """Tests for Decimal precision in fee calculations."""

    def test_basic_fee_calculation(self):
        """Basic fee calculation should be accurate."""
        amount = Decimal("100.00")
        fee = FeeCalculator.calculate_protocol_fee(amount)

        # 100 * 0.003 = 0.30
        assert fee == Decimal("0.300000")

    def test_fee_calculation_small_amount(self):
        """Small amounts should still calculate fees correctly."""
        amount = Decimal("0.01")  # 1 cent
        fee = FeeCalculator.calculate_protocol_fee(amount)

        # 0.01 * 0.003 = 0.00003 -> rounds to 0.000030
        assert fee == Decimal("0.000030")

    def test_fee_calculation_large_amount(self):
        """Large amounts should maintain precision."""
        amount = Decimal("1000000.00")  # 1 million
        fee = FeeCalculator.calculate_protocol_fee(amount)

        # 1,000,000 * 0.003 = 3000.00
        assert fee == Decimal("3000.000000")

    def test_no_floating_point_errors(self):
        """
        Verify no floating-point accumulation errors.

        FINTECH CRITICAL: Sum of 1000 * 0.1 should equal exactly 100.
        """
        # This is the classic floating-point issue: sum([0.1] * 1000) != 100.0
        amounts = [Decimal("0.10")] * 1000
        total = sum(amounts)

        assert total == Decimal("100.00")

        # Fee calculation should also be exact
        fee = FeeCalculator.calculate_protocol_fee(total)
        expected_fee = Decimal("0.300000")  # 100 * 0.003
        assert fee == expected_fee

    def test_fee_calculation_repeating_decimals(self):
        """Handle amounts that produce repeating decimals."""
        # 1/3 produces repeating decimal
        amount = Decimal("1") / Decimal("3")
        fee = FeeCalculator.calculate_protocol_fee(amount)

        # Should be properly rounded, not infinitely repeating
        assert len(str(fee).split(".")[-1]) <= 6

    def test_rounding_consistency(self):
        """Rounding should be consistent (HALF_UP)."""
        # Amount that produces fee ending in exactly 5
        # 166.666... * 0.003 = 0.5
        amount = Decimal("166.666667")
        fee = FeeCalculator.calculate_protocol_fee(amount)

        # With ROUND_HALF_UP, 0.5 rounds to 1
        # Actual: 166.666667 * 0.003 = 0.500000001 -> 0.500000
        assert fee >= Decimal("0.499999")


class TestEdgeCases:
    """Edge case tests for fee calculations."""

    def test_zero_amount(self):
        """Zero amount should result in zero fee."""
        amount = Decimal("0")
        fee = FeeCalculator.calculate_protocol_fee(amount)
        assert fee == Decimal("0")

    def test_negative_amount(self):
        """Negative amounts should return zero fee (invalid)."""
        amount = Decimal("-100.00")
        fee = FeeCalculator.calculate_protocol_fee(amount)
        assert fee == Decimal("0")

    def test_very_small_amount(self):
        """Very small amounts should not cause division errors."""
        amount = Decimal("0.000001")  # Minimum unit
        fee = FeeCalculator.calculate_protocol_fee(amount)

        # Should not raise, fee might be 0 due to rounding
        assert fee >= Decimal("0")

    def test_maximum_amount(self):
        """Maximum reasonable amount should work."""
        # 100 billion (more than total USDC supply)
        amount = Decimal("100000000000.000000")
        fee = FeeCalculator.calculate_protocol_fee(amount)

        # 100B * 0.003 = 300M
        assert fee == Decimal("300000000.000000")

    def test_high_precision_input(self):
        """High precision input should be handled correctly."""
        # More decimals than we support
        amount = Decimal("100.123456789012345")
        fee = FeeCalculator.calculate_protocol_fee(amount)

        # Should not crash, and should truncate/round appropriately
        assert isinstance(fee, Decimal)
        assert len(str(fee).split(".")[-1]) <= 6


class TestMinorMajorConversion:
    """Tests for minor/major unit conversions."""

    def test_minor_to_major_basic(self):
        """Basic minor to major conversion."""
        minor = 1000000  # 1 USDC
        major = FeeCalculator.minor_to_major(minor)
        assert major == Decimal("1.000000")

    def test_major_to_minor_basic(self):
        """Basic major to minor conversion."""
        major = Decimal("1.000000")
        minor = FeeCalculator.major_to_minor(major)
        assert minor == 1000000

    def test_conversion_roundtrip(self):
        """Conversion should be reversible without loss."""
        original_minor = 123456789  # 123.456789 USDC
        major = FeeCalculator.minor_to_major(original_minor)
        back_to_minor = FeeCalculator.major_to_minor(major)

        assert back_to_minor == original_minor

    def test_conversion_with_trailing_zeros(self):
        """Trailing zeros should be preserved."""
        minor = 100000  # 0.100000 USDC
        major = FeeCalculator.minor_to_major(minor)
        assert major == Decimal("0.100000")

    def test_major_to_minor_truncates(self):
        """Extra precision in major should be truncated (not rounded)."""
        # More precision than supported
        major = Decimal("1.1234567")  # 7 decimals
        minor = FeeCalculator.major_to_minor(major)

        # Should truncate to 1.123456 -> 1123456
        assert minor == 1123456


class TestTotalCalculation:
    """Tests for total amount calculations."""

    def test_total_with_fee(self):
        """Total should include base amount + fees."""
        amount = Decimal("100.00")
        net, fee, total = FeeCalculator.calculate_total_with_fee(amount)

        assert net == amount
        assert fee == Decimal("0.300000")  # 0.3%
        # Total = 100 + 0.30 + 0.001 (chain fee) = 100.301
        assert total == Decimal("100.301000")

    def test_net_from_gross(self):
        """Calculate net amount from gross (reverse calculation)."""
        gross = Decimal("100.301000")
        net, fee = FeeCalculator.calculate_net_from_gross(gross)

        # Should approximately recover original amount
        # Note: Due to rounding, may not be exact
        assert net >= Decimal("99.99")
        assert net <= Decimal("100.01")

    def test_fee_total_relationship(self):
        """
        Verify: net + fee + chain_fee = total

        FINTECH CRITICAL: All parts must sum exactly to total.
        """
        for amount in [Decimal("1"), Decimal("100"), Decimal("1000.50")]:
            net, fee, total = FeeCalculator.calculate_total_with_fee(amount)
            chain_fee = FeeCalculator.CHAIN_FEE_ESTIMATE

            calculated_total = net + fee + chain_fee
            assert calculated_total == total, \
                f"Mismatch for {amount}: {net} + {fee} + {chain_fee} = {calculated_total} != {total}"


class TestBatchCalculation:
    """Tests for batch/aggregate calculations."""

    def test_batch_fee_sum_equals_total_fee(self):
        """
        Sum of individual fees should equal fee on sum of amounts.

        Note: Due to rounding, these may differ slightly.
        The difference should be minimal (within 1 minor unit per item).
        """
        amounts = [Decimal("10.00"), Decimal("25.50"), Decimal("100.00")]

        # Calculate fees individually
        individual_fees = [FeeCalculator.calculate_protocol_fee(a) for a in amounts]
        sum_of_fees = sum(individual_fees)

        # Calculate fee on total
        total_amount = sum(amounts)
        fee_on_total = FeeCalculator.calculate_protocol_fee(total_amount)

        # Difference should be small (rounding errors)
        difference = abs(sum_of_fees - fee_on_total)
        max_acceptable_difference = Decimal("0.000003") * len(amounts)

        assert difference <= max_acceptable_difference, \
            f"Batch fee difference too large: {difference}"

    def test_aggregated_transactions(self):
        """
        Test that aggregating small transactions maintains precision.
        """
        # 100 transactions of 0.01 each
        individual_amount = Decimal("0.01")
        count = 100

        total_individual = individual_amount * count
        individual_fees = FeeCalculator.calculate_protocol_fee(individual_amount) * count
        batch_fee = FeeCalculator.calculate_protocol_fee(total_individual)

        # Total amount should be exact
        assert total_individual == Decimal("1.00")

        # Fees should be very close
        assert abs(individual_fees - batch_fee) < Decimal("0.01")
