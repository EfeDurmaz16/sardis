"""
Compliance dashboard data endpoints module.

Provides data aggregation and metrics for compliance dashboards:
- Real-time compliance metrics
- Historical trend analysis
- Alert management
- Risk distribution
- Screening statistics
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Severity levels for compliance alerts."""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Status of compliance alerts."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class MetricType(str, Enum):
    """Types of compliance metrics."""
    TRANSACTIONS = "transactions"
    SCREENINGS = "screenings"
    ALERTS = "alerts"
    RISK_SCORE = "risk_score"
    APPROVAL_RATE = "approval_rate"
    PEP_MATCHES = "pep_matches"
    SANCTIONS_HITS = "sanctions_hits"
    ADVERSE_MEDIA = "adverse_media"


@dataclass
class ComplianceAlert:
    """A compliance alert requiring attention."""
    alert_id: str
    severity: AlertSeverity
    category: str
    title: str
    description: str
    subject_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: AlertStatus = AlertStatus.OPEN
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "subject_id": self.subject_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "resolution_notes": self.resolution_notes,
            "metadata": self.metadata,
        }


@dataclass
class MetricDataPoint:
    """A single data point for a metric."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series data for a metric."""
    metric_type: MetricType
    name: str
    data_points: List[MetricDataPoint] = field(default_factory=list)
    aggregation: str = "sum"  # sum, avg, max, min, count

    @property
    def latest_value(self) -> Optional[float]:
        """Get the most recent value."""
        if not self.data_points:
            return None
        return self.data_points[-1].value

    @property
    def total(self) -> float:
        """Sum all values."""
        return sum(dp.value for dp in self.data_points)

    @property
    def average(self) -> float:
        """Average of all values."""
        if not self.data_points:
            return 0.0
        return self.total / len(self.data_points)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_type": self.metric_type.value,
            "name": self.name,
            "data_points": [
                {
                    "timestamp": dp.timestamp.isoformat(),
                    "value": dp.value,
                    "metadata": dp.metadata,
                }
                for dp in self.data_points
            ],
            "aggregation": self.aggregation,
            "latest_value": self.latest_value,
            "total": self.total,
            "average": self.average,
        }


@dataclass
class DashboardSummary:
    """Summary data for compliance dashboard."""
    period_start: datetime
    period_end: datetime
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Key metrics
    total_transactions: int = 0
    approved_transactions: int = 0
    denied_transactions: int = 0
    approval_rate: float = 0.0

    # Screening metrics
    total_screenings: int = 0
    pep_matches: int = 0
    sanctions_hits: int = 0
    adverse_media_hits: int = 0

    # Risk metrics
    average_risk_score: float = 0.0
    high_risk_count: int = 0
    critical_risk_count: int = 0

    # Alert metrics
    open_alerts: int = 0
    critical_alerts: int = 0

    # Breakdowns
    by_country: Dict[str, int] = field(default_factory=dict)
    by_risk_level: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "metrics": {
                "transactions": {
                    "total": self.total_transactions,
                    "approved": self.approved_transactions,
                    "denied": self.denied_transactions,
                    "approval_rate": self.approval_rate,
                },
                "screenings": {
                    "total": self.total_screenings,
                    "pep_matches": self.pep_matches,
                    "sanctions_hits": self.sanctions_hits,
                    "adverse_media_hits": self.adverse_media_hits,
                },
                "risk": {
                    "average_score": self.average_risk_score,
                    "high_risk_count": self.high_risk_count,
                    "critical_risk_count": self.critical_risk_count,
                },
                "alerts": {
                    "open": self.open_alerts,
                    "critical": self.critical_alerts,
                },
            },
            "breakdowns": {
                "by_country": self.by_country,
                "by_risk_level": self.by_risk_level,
                "by_category": self.by_category,
            },
        }


class AlertManager:
    """
    Manages compliance alerts.

    Thread-safe alert management with filtering and assignment.
    """

    def __init__(self):
        self._alerts: Dict[str, ComplianceAlert] = {}
        self._lock = threading.Lock()
        self._counter = 0
        self._subscribers: List[Callable[[ComplianceAlert], None]] = []

    def create_alert(
        self,
        severity: AlertSeverity,
        category: str,
        title: str,
        description: str,
        subject_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ComplianceAlert:
        """Create a new alert."""
        with self._lock:
            self._counter += 1
            alert_id = f"alert_{self._counter:06d}"

            alert = ComplianceAlert(
                alert_id=alert_id,
                severity=severity,
                category=category,
                title=title,
                description=description,
                subject_id=subject_id,
                metadata=metadata or {},
            )

            self._alerts[alert_id] = alert

        # Notify subscribers
        for callback in self._subscribers:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert subscriber callback failed: {e}")

        logger.info(f"Alert created: {alert_id} - {severity.value} - {title}")
        return alert

    def get_alert(self, alert_id: str) -> Optional[ComplianceAlert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def update_alert(
        self,
        alert_id: str,
        status: Optional[AlertStatus] = None,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[ComplianceAlert]:
        """Update an alert."""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None

            if status:
                alert.status = status
            if assigned_to is not None:
                alert.assigned_to = assigned_to
            if resolution_notes is not None:
                alert.resolution_notes = resolution_notes

            alert.updated_at = datetime.now(timezone.utc)

        logger.info(f"Alert updated: {alert_id} - status={alert.status.value}")
        return alert

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        category: Optional[str] = None,
        subject_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ComplianceAlert]:
        """Get alerts with optional filtering."""
        with self._lock:
            alerts = list(self._alerts.values())

        # Apply filters
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if category:
            alerts = [a for a in alerts if a.category == category]
        if subject_id:
            alerts = [a for a in alerts if a.subject_id == subject_id]
        if since:
            alerts = [a for a in alerts if a.created_at >= since]

        # Sort by severity (critical first) then by date
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 3,
        }
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 99), -a.created_at.timestamp()))

        return alerts[:limit]

    def get_open_alerts_count(self) -> Dict[AlertSeverity, int]:
        """Get count of open alerts by severity."""
        counts = {s: 0 for s in AlertSeverity}
        for alert in self._alerts.values():
            if alert.status == AlertStatus.OPEN:
                counts[alert.severity] += 1
        return counts

    def subscribe(self, callback: Callable[[ComplianceAlert], None]) -> None:
        """Subscribe to new alert notifications."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[ComplianceAlert], None]) -> None:
        """Unsubscribe from alert notifications."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)


class MetricsCollector:
    """
    Collects and aggregates compliance metrics.

    Thread-safe metrics collection with time-based aggregation.
    """

    def __init__(self, retention_days: int = 90):
        self._retention_days = retention_days
        self._metrics: Dict[str, List[MetricDataPoint]] = defaultdict(list)
        self._lock = threading.Lock()

    def record(
        self,
        metric_type: MetricType,
        value: float,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a metric value."""
        timestamp = timestamp or datetime.now(timezone.utc)
        key = f"{metric_type.value}:{name or 'default'}"

        with self._lock:
            self._metrics[key].append(MetricDataPoint(
                timestamp=timestamp,
                value=value,
                metadata=metadata or {},
            ))
            self._cleanup_old_metrics(key)

    def _cleanup_old_metrics(self, key: str) -> None:
        """Remove metrics older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        self._metrics[key] = [
            dp for dp in self._metrics[key]
            if dp.timestamp > cutoff
        ]

    def get_series(
        self,
        metric_type: MetricType,
        name: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> MetricSeries:
        """Get metric time series."""
        key = f"{metric_type.value}:{name or 'default'}"

        with self._lock:
            data_points = list(self._metrics.get(key, []))

        # Filter by time range
        if start:
            data_points = [dp for dp in data_points if dp.timestamp >= start]
        if end:
            data_points = [dp for dp in data_points if dp.timestamp <= end]

        # Sort by timestamp
        data_points.sort(key=lambda dp: dp.timestamp)

        return MetricSeries(
            metric_type=metric_type,
            name=name or "default",
            data_points=data_points,
        )

    def get_aggregated(
        self,
        metric_type: MetricType,
        name: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        interval: str = "hour",  # hour, day, week
    ) -> List[Dict[str, Any]]:
        """Get aggregated metric data."""
        series = self.get_series(metric_type, name, start, end)

        # Group by interval
        buckets: Dict[str, List[float]] = defaultdict(list)

        for dp in series.data_points:
            if interval == "hour":
                bucket_key = dp.timestamp.strftime("%Y-%m-%d %H:00")
            elif interval == "day":
                bucket_key = dp.timestamp.strftime("%Y-%m-%d")
            elif interval == "week":
                # ISO week
                bucket_key = dp.timestamp.strftime("%Y-W%W")
            else:
                bucket_key = dp.timestamp.strftime("%Y-%m-%d")

            buckets[bucket_key].append(dp.value)

        # Aggregate each bucket
        result = []
        for bucket_key in sorted(buckets.keys()):
            values = buckets[bucket_key]
            result.append({
                "period": bucket_key,
                "sum": sum(values),
                "avg": sum(values) / len(values) if values else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "count": len(values),
            })

        return result

    def get_current_totals(
        self,
        since: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Get current totals for all metrics."""
        since = since or (datetime.now(timezone.utc) - timedelta(hours=24))
        totals = {}

        with self._lock:
            for key, data_points in self._metrics.items():
                metric_type, name = key.split(":", 1)
                filtered = [dp for dp in data_points if dp.timestamp >= since]
                totals[key] = sum(dp.value for dp in filtered)

        return totals


class ComplianceDashboard:
    """
    Main compliance dashboard service.

    Aggregates data from various sources for dashboard display.
    """

    def __init__(
        self,
        alert_manager: Optional[AlertManager] = None,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        self._alert_manager = alert_manager or AlertManager()
        self._metrics = metrics_collector or MetricsCollector()
        self._audit_entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record_transaction(
        self,
        mandate_id: str,
        allowed: bool,
        amount: float,
        risk_score: float,
        country: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a transaction for dashboard metrics."""
        # Record transaction metric
        self._metrics.record(
            MetricType.TRANSACTIONS,
            value=1,
            name="total",
            metadata={"mandate_id": mandate_id, "allowed": allowed},
        )

        # Record approval/denial
        status_name = "approved" if allowed else "denied"
        self._metrics.record(MetricType.TRANSACTIONS, value=1, name=status_name)

        # Record risk score
        self._metrics.record(
            MetricType.RISK_SCORE,
            value=risk_score,
            metadata={"mandate_id": mandate_id},
        )

        # Store audit entry
        with self._lock:
            self._audit_entries.append({
                "mandate_id": mandate_id,
                "allowed": allowed,
                "amount": amount,
                "risk_score": risk_score,
                "country": country,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            })
            # Keep only recent entries
            if len(self._audit_entries) > 100000:
                self._audit_entries = self._audit_entries[-50000:]

        # Create alert for high-risk denied transactions
        if not allowed and risk_score >= 80:
            self._alert_manager.create_alert(
                severity=AlertSeverity.HIGH,
                category="transaction",
                title="High-Risk Transaction Denied",
                description=f"Transaction {mandate_id} denied with risk score {risk_score:.1f}",
                metadata=metadata,
            )

    def record_screening(
        self,
        screening_type: str,
        subject_id: str,
        is_match: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a screening result."""
        self._metrics.record(MetricType.SCREENINGS, value=1, name="total")

        if screening_type == "pep":
            if is_match:
                self._metrics.record(MetricType.PEP_MATCHES, value=1)
        elif screening_type == "sanctions":
            if is_match:
                self._metrics.record(MetricType.SANCTIONS_HITS, value=1)
                # Create critical alert for sanctions hit
                self._alert_manager.create_alert(
                    severity=AlertSeverity.CRITICAL,
                    category="sanctions",
                    title="Sanctions Match Detected",
                    description=f"Subject {subject_id} matched sanctions list",
                    subject_id=subject_id,
                    metadata=details,
                )
        elif screening_type == "adverse_media":
            if is_match:
                self._metrics.record(MetricType.ADVERSE_MEDIA, value=1)

    def get_summary(
        self,
        period_hours: int = 24,
    ) -> DashboardSummary:
        """Get dashboard summary for a time period."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=period_hours)

        # Get transaction metrics
        total_series = self._metrics.get_series(MetricType.TRANSACTIONS, "total", start, end)
        approved_series = self._metrics.get_series(MetricType.TRANSACTIONS, "approved", start, end)
        denied_series = self._metrics.get_series(MetricType.TRANSACTIONS, "denied", start, end)

        total = int(total_series.total)
        approved = int(approved_series.total)
        denied = int(denied_series.total)
        approval_rate = (approved / total * 100) if total > 0 else 0.0

        # Get screening metrics
        screenings = int(self._metrics.get_series(MetricType.SCREENINGS, "total", start, end).total)
        pep_matches = int(self._metrics.get_series(MetricType.PEP_MATCHES, start=start, end=end).total)
        sanctions_hits = int(self._metrics.get_series(MetricType.SANCTIONS_HITS, start=start, end=end).total)
        adverse_media = int(self._metrics.get_series(MetricType.ADVERSE_MEDIA, start=start, end=end).total)

        # Get risk metrics
        risk_series = self._metrics.get_series(MetricType.RISK_SCORE, start=start, end=end)
        avg_risk = risk_series.average

        # Count high and critical risk
        with self._lock:
            recent_entries = [
                e for e in self._audit_entries
                if datetime.fromisoformat(e["timestamp"]) >= start
            ]

        high_risk = sum(1 for e in recent_entries if 60 <= e.get("risk_score", 0) < 80)
        critical_risk = sum(1 for e in recent_entries if e.get("risk_score", 0) >= 80)

        # Get alert counts
        alert_counts = self._alert_manager.get_open_alerts_count()
        open_alerts = sum(alert_counts.values())
        critical_alerts = alert_counts.get(AlertSeverity.CRITICAL, 0)

        # Calculate breakdowns
        by_country: Dict[str, int] = defaultdict(int)
        by_risk_level: Dict[str, int] = defaultdict(int)

        for entry in recent_entries:
            country = entry.get("country", "unknown")
            by_country[country] += 1

            risk = entry.get("risk_score", 0)
            if risk < 30:
                by_risk_level["low"] += 1
            elif risk < 60:
                by_risk_level["medium"] += 1
            elif risk < 80:
                by_risk_level["high"] += 1
            else:
                by_risk_level["critical"] += 1

        return DashboardSummary(
            period_start=start,
            period_end=end,
            total_transactions=total,
            approved_transactions=approved,
            denied_transactions=denied,
            approval_rate=approval_rate,
            total_screenings=screenings,
            pep_matches=pep_matches,
            sanctions_hits=sanctions_hits,
            adverse_media_hits=adverse_media,
            average_risk_score=avg_risk,
            high_risk_count=high_risk,
            critical_risk_count=critical_risk,
            open_alerts=open_alerts,
            critical_alerts=critical_alerts,
            by_country=dict(by_country),
            by_risk_level=dict(by_risk_level),
        )

    def get_trend_data(
        self,
        metric_type: MetricType,
        days: int = 7,
        interval: str = "day",
    ) -> List[Dict[str, Any]]:
        """Get trend data for a metric."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return self._metrics.get_aggregated(metric_type, start=start, end=end, interval=interval)

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50,
    ) -> List[ComplianceAlert]:
        """Get compliance alerts."""
        return self._alert_manager.get_alerts(
            status=status,
            severity=severity,
            limit=limit,
        )

    def create_alert(
        self,
        severity: AlertSeverity,
        category: str,
        title: str,
        description: str,
        **kwargs,
    ) -> ComplianceAlert:
        """Create a new alert."""
        return self._alert_manager.create_alert(
            severity=severity,
            category=category,
            title=title,
            description=description,
            **kwargs,
        )

    def update_alert(
        self,
        alert_id: str,
        status: Optional[AlertStatus] = None,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[ComplianceAlert]:
        """Update an alert."""
        return self._alert_manager.update_alert(
            alert_id=alert_id,
            status=status,
            assigned_to=assigned_to,
            resolution_notes=resolution_notes,
        )

    @property
    def alert_manager(self) -> AlertManager:
        """Get the alert manager."""
        return self._alert_manager

    @property
    def metrics_collector(self) -> MetricsCollector:
        """Get the metrics collector."""
        return self._metrics


def create_dashboard() -> ComplianceDashboard:
    """Factory function to create a ComplianceDashboard instance."""
    return ComplianceDashboard()
