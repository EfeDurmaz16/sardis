"""
Example: Integrating real-time alerts into payment flows

This example demonstrates how to:
1. Configure alert rules and channels
2. Emit alerts during payment execution
3. Connect to the WebSocket alert stream
"""

import asyncio
import os
from decimal import Decimal

# Example: Emitting alerts from payment execution
async def payment_with_alerts_example():
    """
    Example showing how to emit alerts during payment execution.

    This would typically be integrated into the payment orchestrator or API routes.
    """
    from sardis_v2_core.alert_rules import Alert, AlertType, AlertSeverity
    from sardis_v2_core.alert_channels import AlertDispatcher, SlackChannel, WebSocketChannel

    # Initialize dispatcher
    dispatcher = AlertDispatcher()

    # Register channels
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook:
        dispatcher.register_channel("slack", SlackChannel(slack_webhook))

    # Simulate payment execution
    payment_amount = Decimal("1500.00")
    agent_id = "agent_abc123"
    organization_id = "org_xyz789"

    # Check if amount exceeds threshold
    if payment_amount > Decimal("1000.00"):
        alert = Alert(
            alert_type=AlertType.PAYMENT_EXECUTED,
            severity=AlertSeverity.WARNING,
            message=f"High-value payment of ${payment_amount} executed",
            agent_id=agent_id,
            organization_id=organization_id,
            data={
                "amount": str(payment_amount),
                "threshold": "1000.00",
                "transaction_id": "tx_example123",
            },
        )

        # Dispatch to all configured channels
        results = await dispatcher.dispatch(alert)
        print(f"Alert dispatched to channels: {results}")


async def budget_threshold_alert_example():
    """
    Example showing budget threshold alerts.
    """
    from sardis_v2_core.alert_rules import Alert, AlertType, AlertSeverity
    from sardis_api.routers.alerts import dispatch_alert

    # Simulate budget tracking
    budget_total = Decimal("10000.00")
    budget_used = Decimal("9000.00")
    percentage = (budget_used / budget_total) * 100

    # Check if we've crossed a threshold (90%)
    if percentage >= 90:
        alert = Alert(
            alert_type=AlertType.BUDGET_THRESHOLD,
            severity=AlertSeverity.CRITICAL,
            message=f"Budget at {percentage:.1f}% (${budget_used} of ${budget_total})",
            agent_id="agent_abc123",
            organization_id="org_xyz789",
            data={
                "budget_used": str(budget_used),
                "budget_total": str(budget_total),
                "percentage": float(percentage),
                "threshold": 90.0,
            },
        )

        # Dispatch alert (this would be called from the API)
        await dispatch_alert(alert)


async def policy_violation_alert_example():
    """
    Example showing policy violation alerts.
    """
    from sardis_v2_core.alert_rules import Alert, AlertType, AlertSeverity

    alert = Alert(
        alert_type=AlertType.POLICY_VIOLATION,
        severity=AlertSeverity.CRITICAL,
        message="Transaction blocked: Merchant not in allowlist",
        agent_id="agent_abc123",
        organization_id="org_xyz789",
        data={
            "merchant": "unauthorized-vendor.com",
            "policy_rule": "allowed_merchants",
            "transaction_amount": "250.00",
        },
    )

    # This would be dispatched from the policy engine
    print(f"Policy violation alert: {alert.message}")


async def websocket_client_example():
    """
    Example WebSocket client for receiving real-time alerts.

    This shows how to connect to the alert stream from a Python client.
    """
    import websockets
    import json

    api_url = "ws://localhost:8000"
    token = "org_xyz789"  # Your organization token

    async with websockets.connect(f"{api_url}/api/v2/ws/alerts?token={token}") as ws:
        print("Connected to alert stream")

        # Send pong responses to keep connection alive
        async def heartbeat():
            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(message)

                    if data.get("type") == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                    elif data.get("type") == "system":
                        print(f"System: {data.get('message')}")
                    elif data.get("alert_type"):
                        # This is an alert
                        print(f"\n🔔 ALERT [{data['severity'].upper()}]")
                        print(f"   Type: {data['alert_type']}")
                        print(f"   Message: {data['message']}")
                        print(f"   Agent: {data.get('agent_id', 'N/A')}")
                        print(f"   Time: {data['timestamp']}")

                        # Handle critical alerts
                        if data['severity'] == 'critical':
                            print("   ⚠️  CRITICAL ALERT - Immediate attention required!")

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error: {e}")
                    break

        await heartbeat()


async def configure_rules_example():
    """
    Example showing how to configure alert rules via API.
    """
    import httpx

    api_url = "http://localhost:8000"
    api_key = os.getenv("SARDIS_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Create a custom alert rule
    rule_data = {
        "name": "Large transaction alert",
        "condition_type": "amount_exceeds",
        "threshold": "5000.00",
        "channels": ["websocket", "slack", "email"],
        "enabled": True,
        "metadata": {
            "description": "Alert for transactions over $5000",
        },
    }

    async with httpx.AsyncClient() as client:
        # Create rule
        response = await client.post(
            f"{api_url}/api/v2/alerts/rules",
            headers=headers,
            json=rule_data,
        )

        if response.status_code == 201:
            rule = response.json()
            print(f"Created rule: {rule['id']}")

            # List all rules
            response = await client.get(
                f"{api_url}/api/v2/alerts/rules",
                headers=headers,
            )
            rules = response.json()
            print(f"Total rules: {len(rules)}")

            # Send test alert
            test_data = {
                "alert_type": "payment_executed",
                "severity": "warning",
                "message": "Test alert from example",
                "channels": ["websocket"],
            }

            response = await client.post(
                f"{api_url}/api/v2/alerts/test",
                headers=headers,
                json=test_data,
            )

            if response.status_code == 200:
                result = response.json()
                print(f"Test alert sent: {result['alert_id']}")


async def rule_engine_example():
    """
    Example showing how to use the alert rule engine directly.
    """
    from sardis_v2_core.alert_rules import AlertRuleEngine, AlertRule, ConditionType
    from decimal import Decimal

    # Initialize engine
    engine = AlertRuleEngine()

    # Add custom rule
    custom_rule = AlertRule(
        name="High frequency trading alert",
        condition_type=ConditionType.TRANSACTION_COUNT,
        threshold=Decimal("20"),
        channels=["websocket", "slack"],
        enabled=True,
        metadata={"window_seconds": 300},
    )
    engine.add_rule(custom_rule)

    # Evaluate an event
    event = {
        "event_type": "high_frequency",
        "agent_id": "agent_abc123",
        "organization_id": "org_xyz789",
        "transaction_count": 25,
    }

    alerts = engine.evaluate(event)

    for alert in alerts:
        print(f"Generated alert: {alert.message}")
        print(f"  Severity: {alert.severity.value}")
        print(f"  Data: {alert.data}")


# Integration example for payment orchestrator
async def integrate_alerts_in_orchestrator():
    """
    Example showing how to integrate alerts into the payment orchestrator.

    This would be added to sardis_v2_core/orchestrator.py
    """
    from sardis_v2_core.alert_rules import Alert, AlertType, AlertSeverity
    from sardis_api.routers.alerts import dispatch_alert

    # After successful payment execution:
    async def after_payment_success(
        agent_id: str,
        organization_id: str,
        amount: Decimal,
        transaction_id: str,
    ):
        alert = Alert(
            alert_type=AlertType.PAYMENT_EXECUTED,
            severity=AlertSeverity.INFO,
            message=f"Payment of ${amount} executed successfully",
            agent_id=agent_id,
            organization_id=organization_id,
            data={
                "amount": str(amount),
                "transaction_id": transaction_id,
                "status": "success",
            },
        )
        await dispatch_alert(alert)

    # After policy violation:
    async def after_policy_violation(
        agent_id: str,
        organization_id: str,
        reason: str,
        attempted_amount: Decimal,
    ):
        alert = Alert(
            alert_type=AlertType.POLICY_VIOLATION,
            severity=AlertSeverity.CRITICAL,
            message=f"Policy violation: {reason}",
            agent_id=agent_id,
            organization_id=organization_id,
            data={
                "reason": reason,
                "attempted_amount": str(attempted_amount),
                "status": "blocked",
            },
        )
        await dispatch_alert(alert)


if __name__ == "__main__":
    print("Sardis Alert System Examples")
    print("=" * 50)

    # Run examples
    print("\n1. Payment with alerts:")
    asyncio.run(payment_with_alerts_example())

    print("\n2. Budget threshold alert:")
    asyncio.run(budget_threshold_alert_example())

    print("\n3. Policy violation alert:")
    asyncio.run(policy_violation_alert_example())

    print("\n4. Rule engine example:")
    asyncio.run(rule_engine_example())

    print("\n\nTo run WebSocket client example:")
    print("  python examples/alert_integration_example.py --websocket")

    print("\n\nTo configure rules via API:")
    print("  python examples/alert_integration_example.py --configure")
