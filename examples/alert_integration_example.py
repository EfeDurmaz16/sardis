"""
Real-time alerts via Sardis webhooks — public client SDK.

How to wire real-time operational alerts (high-value payments, policy
violations, budget thresholds) to your own systems using Sardis webhook
subscriptions. Sardis delivers signed events to your HTTPS endpoint; you fan
them out to Slack/email/PagerDuty on your side.

Public surface only: the `sardis` client SDK talks to a hosted Sardis
deployment. Alert routing/dispatch is owned by the backend.

    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com
    export ALERT_WEBHOOK_URL=https://hooks.example.com/sardis   # your receiver
    python examples/alert_integration_example.py
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    from sardis import Sardis

    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    # Where Sardis should POST events. Use a placeholder if not configured so
    # the example is runnable end-to-end against a deployment.
    receiver_url = os.environ.get("ALERT_WEBHOOK_URL", "https://hooks.example.com/sardis")

    client = Sardis(api_key=api_key)

    # 1. Discover which event types the deployment can emit.
    print("Available event types:")
    event_types = client.webhooks.list_event_types()
    for et in event_types:
        print(f"  - {et}")

    # 2. Subscribe to the alert-worthy events. We pick the payment + policy +
    #    budget signals if the deployment exposes them, else subscribe to all.
    wanted = [
        et for et in event_types
        if any(k in et for k in ("payment", "policy", "budget", "approval"))
    ] or event_types

    print(f"\nSubscribing {receiver_url} to {len(wanted)} event types...")
    webhook = client.webhooks.create(
        url=receiver_url,
        events=wanted,
        description="Operational alerts -> internal receiver",
    )
    print(f"  webhook: {webhook.webhook_id}")
    print(f"  active:  {webhook.is_active}")
    print(f"  events:  {', '.join(webhook.events)}")

    # 3. Fire a test delivery so you can confirm your receiver verifies the
    #    signature and parses the payload before any real event arrives.
    print("\nSending a test delivery...")
    delivery = client.webhooks.test(webhook.webhook_id)
    print(f"  delivery:    {delivery.delivery_id}")
    print(f"  status_code: {delivery.status_code}")
    print(f"  success:     {delivery.success}")
    if delivery.error:
        print(f"  error:       {delivery.error}")

    # 4. Inspect recent deliveries (retry/debug surface).
    print("\nRecent deliveries:")
    for d in client.webhooks.list_deliveries(webhook.webhook_id):
        print(f"  {d.created_at}  {d.event_type:<24} -> {d.status_code} (ok={d.success})")

    print("\nReceiver side (your server): verify the signature, then route the")
    print("event to Slack/email/PagerDuty. Sardis owns emission + signing; you")
    print("own fan-out. To stop alerts: client.webhooks.delete(webhook_id).")


if __name__ == "__main__":
    print("Sardis webhook alerting example")
    print("=" * 50)
    main()
