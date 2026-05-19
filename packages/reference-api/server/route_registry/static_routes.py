"""Low-dependency public route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI

from .agents import register_agent_registry_routes
from .authority import (
    register_credential_routes,
    register_mandate_delegation_routes,
    register_mandate_subscription_routes,
)
from .billing import register_usage_routes
from .commerce import (
    register_commerce_support_routes,
    register_escrow_dispute_routes,
    register_service_directory_routes,
)
from .compliance import register_compliance_export_routes
from .developer import register_template_routes
from .evidence import register_evidence_routes
from .money_movement import (
    register_batch_payment_routes,
    register_fx_routes,
    register_payment_object_routes,
    register_receipt_routes,
    register_settlement_routes,
    register_streaming_payment_routes,
)
from .operations import (
    register_dashboard_metrics_routes,
    register_exception_routes,
    register_execution_mode_routes,
    register_outcome_reliability_routes,
)
from .policy import (
    register_fallback_policy_routes,
    register_policy_analytics_routes,
    register_policy_simulation_routes,
)
from .protocol import register_a2a_discovery_routes, register_protocol_v1_routes
from .wallets import register_funding_routes, register_ramp_edge_routes


def register_static_public_routes(app: FastAPI) -> None:
    """Register public routes that do not require app-factory runtime objects."""
    register_service_directory_routes(app)
    register_compliance_export_routes(app)
    register_agent_registry_routes(app)

    register_credential_routes(app)
    register_execution_mode_routes(app)
    register_settlement_routes(app)

    register_policy_simulation_routes(app)
    register_evidence_routes(app)
    register_receipt_routes(app)
    register_outcome_reliability_routes(app)
    register_policy_analytics_routes(app)
    register_exception_routes(app)
    register_template_routes(app)
    register_fallback_policy_routes(app)
    register_commerce_support_routes(app)
    register_dashboard_metrics_routes(app)

    register_payment_object_routes(app)
    register_funding_routes(app)
    register_mandate_delegation_routes(app)
    register_fx_routes(app)
    register_usage_routes(app)
    register_escrow_dispute_routes(app)
    register_batch_payment_routes(app)
    register_mandate_subscription_routes(app)
    register_streaming_payment_routes(app)
    register_protocol_v1_routes(app)
    register_ramp_edge_routes(app)
    register_a2a_discovery_routes(app)
