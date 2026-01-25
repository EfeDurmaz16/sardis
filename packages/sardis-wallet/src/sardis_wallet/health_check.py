"""
Wallet Health Checks for Sardis.

Comprehensive health monitoring for wallet infrastructure including:
- MPC provider connectivity
- Chain connectivity
- Key validity
- Balance monitoring
- Security checks
- Compliance status
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sardis_v2_core import Wallet

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class CheckCategory(str, Enum):
    """Category of health check."""
    CONNECTIVITY = "connectivity"
    SECURITY = "security"
    BALANCE = "balance"
    KEY_MANAGEMENT = "key_management"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    check_id: str
    check_name: str
    category: CheckCategory
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_id": self.check_id,
            "check_name": self.check_name,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "remediation": self.remediation,
        }


@dataclass
class WalletHealthReport:
    """Complete health report for a wallet."""
    wallet_id: str
    overall_status: HealthStatus
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    check_results: List[HealthCheckResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "wallet_id": self.wallet_id,
            "overall_status": self.overall_status.value,
            "generated_at": self.generated_at.isoformat(),
            "check_results": [r.to_dict() for r in self.check_results],
            "summary": self.summary,
            "recommendations": self.recommendations,
        }


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    # Check intervals
    check_interval_seconds: int = 60
    deep_check_interval_seconds: int = 300

    # Thresholds
    min_balance_threshold: Decimal = field(default_factory=lambda: Decimal("1.00"))
    key_expiry_warning_days: int = 14
    max_failed_transactions_percent: float = 10.0
    max_response_time_ms: float = 5000.0

    # Enabled checks
    check_mpc_connectivity: bool = True
    check_chain_connectivity: bool = True
    check_key_validity: bool = True
    check_balance: bool = True
    check_security: bool = True
    check_compliance: bool = True

    # Alert settings
    alert_on_degraded: bool = True
    alert_on_unhealthy: bool = True
    alert_on_critical: bool = True


class MPCProviderChecker(Protocol):
    """Protocol for MPC provider health checks."""

    async def check_connectivity(self) -> Tuple[bool, float]:
        """Check MPC provider connectivity, returns (success, latency_ms)."""
        ...

    async def check_key_status(self, key_reference: str) -> Dict[str, Any]:
        """Check status of an MPC key."""
        ...


class ChainConnectivityChecker(Protocol):
    """Protocol for chain connectivity checks."""

    async def check_chain(self, chain: str) -> Tuple[bool, float, int]:
        """Check chain connectivity, returns (success, latency_ms, block_number)."""
        ...

    async def check_balance(
        self,
        address: str,
        chain: str,
        token: str,
    ) -> Decimal:
        """Check token balance."""
        ...


class HealthChecker:
    """
    Performs comprehensive health checks for wallets.

    Features:
    - MPC provider connectivity
    - Chain connectivity
    - Key validity checks
    - Balance monitoring
    - Security assessments
    - Compliance status
    """

    def __init__(
        self,
        config: Optional[HealthCheckConfig] = None,
        mpc_checker: Optional[MPCProviderChecker] = None,
        chain_checker: Optional[ChainConnectivityChecker] = None,
    ):
        self._config = config or HealthCheckConfig()
        self._mpc_checker = mpc_checker
        self._chain_checker = chain_checker

        # Cache for check results
        self._last_results: Dict[str, WalletHealthReport] = {}
        self._check_history: Dict[str, List[HealthCheckResult]] = {}

        # Background check task
        self._background_task: Optional[asyncio.Task] = None

    async def check_wallet_health(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
        deep_check: bool = False,
    ) -> WalletHealthReport:
        """
        Perform comprehensive health check on a wallet.

        Args:
            wallet_id: Wallet identifier
            wallet_data: Wallet configuration and state
            deep_check: Perform deeper, slower checks

        Returns:
            WalletHealthReport with all check results
        """
        results: List[HealthCheckResult] = []

        # MPC connectivity check
        if self._config.check_mpc_connectivity:
            result = await self._check_mpc_connectivity(wallet_id, wallet_data)
            results.append(result)

        # Chain connectivity checks
        if self._config.check_chain_connectivity:
            chain_results = await self._check_chain_connectivity(wallet_id, wallet_data)
            results.extend(chain_results)

        # Key validity checks
        if self._config.check_key_validity:
            key_results = await self._check_key_validity(wallet_id, wallet_data)
            results.extend(key_results)

        # Balance checks
        if self._config.check_balance:
            balance_results = await self._check_balances(wallet_id, wallet_data)
            results.extend(balance_results)

        # Security checks
        if self._config.check_security:
            security_results = await self._check_security(wallet_id, wallet_data)
            results.extend(security_results)

        # Compliance checks
        if self._config.check_compliance:
            compliance_results = await self._check_compliance(wallet_id, wallet_data)
            results.extend(compliance_results)

        # Deep checks
        if deep_check:
            deep_results = await self._perform_deep_checks(wallet_id, wallet_data)
            results.extend(deep_results)

        # Calculate overall status
        overall_status = self._calculate_overall_status(results)

        # Generate recommendations
        recommendations = self._generate_recommendations(results)

        # Generate summary
        summary = self._generate_summary(results)

        report = WalletHealthReport(
            wallet_id=wallet_id,
            overall_status=overall_status,
            check_results=results,
            summary=summary,
            recommendations=recommendations,
        )

        # Cache result
        self._last_results[wallet_id] = report

        # Store history
        if wallet_id not in self._check_history:
            self._check_history[wallet_id] = []
        self._check_history[wallet_id].extend(results)

        # Keep only last 1000 results per wallet
        if len(self._check_history[wallet_id]) > 1000:
            self._check_history[wallet_id] = self._check_history[wallet_id][-1000:]

        return report

    async def _check_mpc_connectivity(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
    ) -> HealthCheckResult:
        """Check MPC provider connectivity."""
        import time

        start_time = time.time()

        try:
            if self._mpc_checker:
                success, latency = await self._mpc_checker.check_connectivity()
            else:
                # Mock check
                await asyncio.sleep(0.1)
                success, latency = True, 100.0

            duration = (time.time() - start_time) * 1000

            if success:
                if latency > self._config.max_response_time_ms:
                    status = HealthStatus.DEGRADED
                    message = f"MPC provider slow: {latency:.0f}ms"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"MPC provider connected: {latency:.0f}ms"
            else:
                status = HealthStatus.UNHEALTHY
                message = "MPC provider unreachable"

            return HealthCheckResult(
                check_id=f"mpc_connectivity_{wallet_id[:8]}",
                check_name="MPC Provider Connectivity",
                category=CheckCategory.CONNECTIVITY,
                status=status,
                message=message,
                details={"latency_ms": latency},
                duration_ms=duration,
            )

        except Exception as e:
            return HealthCheckResult(
                check_id=f"mpc_connectivity_{wallet_id[:8]}",
                check_name="MPC Provider Connectivity",
                category=CheckCategory.CONNECTIVITY,
                status=HealthStatus.CRITICAL,
                message=f"MPC check failed: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
                remediation="Check MPC provider configuration and network connectivity",
            )

    async def _check_chain_connectivity(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
    ) -> List[HealthCheckResult]:
        """Check blockchain connectivity for all configured chains."""
        import time

        results = []
        addresses = wallet_data.get("addresses", {})

        for chain in addresses.keys():
            start_time = time.time()

            try:
                if self._chain_checker:
                    success, latency, block = await self._chain_checker.check_chain(chain)
                else:
                    # Mock check
                    await asyncio.sleep(0.05)
                    success, latency, block = True, 50.0, 12345678

                duration = (time.time() - start_time) * 1000

                if success:
                    if latency > self._config.max_response_time_ms:
                        status = HealthStatus.DEGRADED
                        message = f"{chain} RPC slow: {latency:.0f}ms"
                    else:
                        status = HealthStatus.HEALTHY
                        message = f"{chain} connected at block {block}"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"{chain} RPC unreachable"

                results.append(HealthCheckResult(
                    check_id=f"chain_{chain}_{wallet_id[:8]}",
                    check_name=f"{chain.capitalize()} Chain Connectivity",
                    category=CheckCategory.CONNECTIVITY,
                    status=status,
                    message=message,
                    details={"chain": chain, "latency_ms": latency, "block_number": block},
                    duration_ms=duration,
                ))

            except Exception as e:
                results.append(HealthCheckResult(
                    check_id=f"chain_{chain}_{wallet_id[:8]}",
                    check_name=f"{chain.capitalize()} Chain Connectivity",
                    category=CheckCategory.CONNECTIVITY,
                    status=HealthStatus.CRITICAL,
                    message=f"{chain} check failed: {str(e)}",
                    duration_ms=(time.time() - start_time) * 1000,
                    remediation=f"Check {chain} RPC configuration",
                ))

        return results

    async def _check_key_validity(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
    ) -> List[HealthCheckResult]:
        """Check validity of MPC keys."""
        results = []

        keys = wallet_data.get("keys", [])
        if not keys:
            # Check if wallet has key reference
            key_ref = wallet_data.get("mpc_key_reference")
            if key_ref:
                keys = [{"key_id": key_ref, "expires_at": wallet_data.get("key_expires_at")}]

        for key in keys:
            key_id = key.get("key_id", "unknown")
            expires_at = key.get("expires_at")

            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)

                days_until_expiry = (expires_at - datetime.now(timezone.utc)).days

                if days_until_expiry < 0:
                    status = HealthStatus.CRITICAL
                    message = f"Key {key_id[:8]}... has expired"
                    remediation = "Rotate key immediately"
                elif days_until_expiry < self._config.key_expiry_warning_days:
                    status = HealthStatus.DEGRADED
                    message = f"Key {key_id[:8]}... expires in {days_until_expiry} days"
                    remediation = "Schedule key rotation"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Key {key_id[:8]}... valid for {days_until_expiry} days"
                    remediation = None

                results.append(HealthCheckResult(
                    check_id=f"key_{key_id[:8]}_{wallet_id[:8]}",
                    check_name=f"Key Validity ({key_id[:8]}...)",
                    category=CheckCategory.KEY_MANAGEMENT,
                    status=status,
                    message=message,
                    details={"key_id": key_id, "days_until_expiry": days_until_expiry},
                    remediation=remediation,
                ))

        if not results:
            results.append(HealthCheckResult(
                check_id=f"key_check_{wallet_id[:8]}",
                check_name="Key Validity",
                category=CheckCategory.KEY_MANAGEMENT,
                status=HealthStatus.UNKNOWN,
                message="No key information available",
                remediation="Verify wallet key configuration",
            ))

        return results

    async def _check_balances(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
    ) -> List[HealthCheckResult]:
        """Check wallet balances."""
        results = []
        addresses = wallet_data.get("addresses", {})
        tokens = wallet_data.get("tokens", ["USDC"])

        for chain, address in addresses.items():
            for token in tokens:
                try:
                    if self._chain_checker:
                        balance = await self._chain_checker.check_balance(address, chain, token)
                    else:
                        # Mock balance
                        balance = Decimal("100.00")

                    if balance < self._config.min_balance_threshold:
                        status = HealthStatus.DEGRADED
                        message = f"Low {token} balance on {chain}: {balance}"
                        remediation = f"Consider topping up {token} on {chain}"
                    else:
                        status = HealthStatus.HEALTHY
                        message = f"{token} balance on {chain}: {balance}"
                        remediation = None

                    results.append(HealthCheckResult(
                        check_id=f"balance_{chain}_{token}_{wallet_id[:8]}",
                        check_name=f"{token} Balance on {chain.capitalize()}",
                        category=CheckCategory.BALANCE,
                        status=status,
                        message=message,
                        details={"chain": chain, "token": token, "balance": str(balance)},
                        remediation=remediation,
                    ))

                except Exception as e:
                    results.append(HealthCheckResult(
                        check_id=f"balance_{chain}_{token}_{wallet_id[:8]}",
                        check_name=f"{token} Balance on {chain.capitalize()}",
                        category=CheckCategory.BALANCE,
                        status=HealthStatus.UNKNOWN,
                        message=f"Balance check failed: {str(e)}",
                    ))

        return results

    async def _check_security(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
    ) -> List[HealthCheckResult]:
        """Check security configuration."""
        results = []

        # Check MFA status
        mfa_enabled = wallet_data.get("mfa_enabled", False)
        if mfa_enabled:
            status = HealthStatus.HEALTHY
            message = "MFA is enabled"
        else:
            status = HealthStatus.DEGRADED
            message = "MFA is not enabled"

        results.append(HealthCheckResult(
            check_id=f"security_mfa_{wallet_id[:8]}",
            check_name="Multi-Factor Authentication",
            category=CheckCategory.SECURITY,
            status=status,
            message=message,
            remediation="Enable MFA for improved security" if not mfa_enabled else None,
        ))

        # Check backup status
        has_backup = wallet_data.get("has_backup", False)
        backup_age_days = wallet_data.get("backup_age_days")

        if not has_backup:
            status = HealthStatus.DEGRADED
            message = "No backup configured"
            remediation = "Create a wallet backup"
        elif backup_age_days and backup_age_days > 90:
            status = HealthStatus.DEGRADED
            message = f"Backup is {backup_age_days} days old"
            remediation = "Create a fresh backup"
        else:
            status = HealthStatus.HEALTHY
            message = "Backup is up to date"
            remediation = None

        results.append(HealthCheckResult(
            check_id=f"security_backup_{wallet_id[:8]}",
            check_name="Backup Status",
            category=CheckCategory.SECURITY,
            status=status,
            message=message,
            remediation=remediation,
        ))

        # Check social recovery
        has_recovery = wallet_data.get("has_social_recovery", False)
        guardian_count = wallet_data.get("guardian_count", 0)

        if has_recovery and guardian_count >= 3:
            status = HealthStatus.HEALTHY
            message = f"Social recovery configured with {guardian_count} guardians"
        elif has_recovery:
            status = HealthStatus.DEGRADED
            message = f"Social recovery has only {guardian_count} guardians"
            remediation = "Add more guardians for better recovery security"
        else:
            status = HealthStatus.DEGRADED
            message = "Social recovery not configured"
            remediation = "Set up social recovery"

        results.append(HealthCheckResult(
            check_id=f"security_recovery_{wallet_id[:8]}",
            check_name="Social Recovery",
            category=CheckCategory.SECURITY,
            status=status,
            message=message,
            remediation=remediation if status != HealthStatus.HEALTHY else None,
        ))

        return results

    async def _check_compliance(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
    ) -> List[HealthCheckResult]:
        """Check compliance status."""
        results = []

        # KYC status
        kyc_status = wallet_data.get("kyc_status", "none")
        kyc_expiry = wallet_data.get("kyc_expiry")

        if kyc_status == "verified":
            if kyc_expiry:
                expiry_date = datetime.fromisoformat(kyc_expiry) if isinstance(kyc_expiry, str) else kyc_expiry
                days_until_expiry = (expiry_date - datetime.now(timezone.utc)).days

                if days_until_expiry < 0:
                    status = HealthStatus.UNHEALTHY
                    message = "KYC has expired"
                    remediation = "Complete KYC re-verification"
                elif days_until_expiry < 30:
                    status = HealthStatus.DEGRADED
                    message = f"KYC expires in {days_until_expiry} days"
                    remediation = "Schedule KYC renewal"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"KYC verified, expires in {days_until_expiry} days"
                    remediation = None
            else:
                status = HealthStatus.HEALTHY
                message = "KYC verified"
                remediation = None
        elif kyc_status == "pending":
            status = HealthStatus.DEGRADED
            message = "KYC verification pending"
            remediation = "Complete KYC verification"
        else:
            status = HealthStatus.DEGRADED
            message = "KYC not completed"
            remediation = "Start KYC verification process"

        results.append(HealthCheckResult(
            check_id=f"compliance_kyc_{wallet_id[:8]}",
            check_name="KYC Status",
            category=CheckCategory.COMPLIANCE,
            status=status,
            message=message,
            remediation=remediation,
        ))

        return results

    async def _perform_deep_checks(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
    ) -> List[HealthCheckResult]:
        """Perform deeper, more comprehensive checks."""
        results = []

        # Transaction success rate check
        tx_success_rate = wallet_data.get("tx_success_rate", 100.0)
        if tx_success_rate < 100 - self._config.max_failed_transactions_percent:
            status = HealthStatus.DEGRADED
            message = f"Transaction success rate: {tx_success_rate:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Transaction success rate: {tx_success_rate:.1f}%"

        results.append(HealthCheckResult(
            check_id=f"deep_tx_rate_{wallet_id[:8]}",
            check_name="Transaction Success Rate",
            category=CheckCategory.PERFORMANCE,
            status=status,
            message=message,
            details={"success_rate_percent": tx_success_rate},
        ))

        return results

    def _calculate_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Calculate overall health status from individual checks."""
        if not results:
            return HealthStatus.UNKNOWN

        status_priority = {
            HealthStatus.CRITICAL: 4,
            HealthStatus.UNHEALTHY: 3,
            HealthStatus.DEGRADED: 2,
            HealthStatus.HEALTHY: 1,
            HealthStatus.UNKNOWN: 0,
        }

        worst_status = HealthStatus.HEALTHY
        worst_priority = 1

        for result in results:
            priority = status_priority.get(result.status, 0)
            if priority > worst_priority:
                worst_priority = priority
                worst_status = result.status

        return worst_status

    def _generate_recommendations(self, results: List[HealthCheckResult]) -> List[str]:
        """Generate recommendations based on check results."""
        recommendations = []

        for result in results:
            if result.remediation and result.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
                recommendations.append(result.remediation)

        return list(set(recommendations))  # Remove duplicates

    def _generate_summary(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Generate summary statistics from check results."""
        status_counts = {status.value: 0 for status in HealthStatus}
        category_counts = {cat.value: 0 for cat in CheckCategory}
        total_duration = 0.0

        for result in results:
            status_counts[result.status.value] += 1
            category_counts[result.category.value] += 1
            total_duration += result.duration_ms

        return {
            "total_checks": len(results),
            "status_counts": status_counts,
            "category_counts": category_counts,
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration / len(results) if results else 0,
        }

    def get_last_report(self, wallet_id: str) -> Optional[WalletHealthReport]:
        """Get the last health report for a wallet."""
        return self._last_results.get(wallet_id)

    def get_check_history(
        self,
        wallet_id: str,
        category: Optional[CheckCategory] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get check history for a wallet."""
        history = self._check_history.get(wallet_id, [])

        if category:
            history = [h for h in history if h.category == category]

        return [h.to_dict() for h in sorted(history, key=lambda h: h.timestamp, reverse=True)[:limit]]


# Singleton instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker(
    config: Optional[HealthCheckConfig] = None,
) -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker

    if _health_checker is None:
        _health_checker = HealthChecker(config)

    return _health_checker


__all__ = [
    "HealthStatus",
    "CheckCategory",
    "HealthCheckResult",
    "WalletHealthReport",
    "HealthCheckConfig",
    "HealthChecker",
    "get_health_checker",
]
