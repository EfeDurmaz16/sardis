#!/usr/bin/env python3
"""
Sardis Webhooks — subscribe, manage, and verify deliveries (public client SDK)
==============================================================================

Sardis emits events (payment completed, policy violated, approval requested,
spend thresholds) to webhook subscriptions. This example shows the full
subscription lifecycle through the public `sardis` client SDK plus the
receiver-side signature check you implement on your own server.

Public surface only: the client talks to a hosted Sardis deployment. Event
emission, signing, and delivery are owned by the backend.

Prerequisites:
    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com
    export EVENT_WEBHOOK_URL=https://hooks.example.com/sardis   # your receiver

Run:
    python examples/event_webhooks.py
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys

# --- Receiver-side helper (runs on YOUR server, not in Sardis) --------------

def verify_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify a Sardis webhook delivery on your receiver.

    Sardis signs the raw request body with the subscription's signing secret
    (HMAC-SHA256). Recompute and constant-time compare before trusting the
    payload. `secret` is what `webhooks.rotate_secret(...)` returns.
    """
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # Accept either "sha256=<hex>" or bare hex in the header.
    candidate = signature_header.split("=", 1)[-1].strip()
    return hmac.compare_digest(expected, candidate)


def _demo_signature_roundtrip() -> None:
    """Illustrate the receiver-side verify with a known secret + body."""
    # Placeholder only — your real secret comes from webhooks.rotate_secret().
    secret = "REPLACE_WITH_YOUR_WEBHOOK_SIGNING_SECRET"  # noqa: S105
    body = json.dumps({"event_type": "payment.completed", "amount": "25.00"}).encode()
    header = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    print("Receiver-side verification:")
    print(f"  valid signature   -> {verify_signature(body, header, secret)}")
    print(f"  tampered body     -> {verify_signature(body + b'x', header, secret)}")


# --- Subscription management (runs against the Sardis API) ------------------

def main() -> None:
    from sardis import Sardis

    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    receiver_url = os.environ.get("EVENT_WEBHOOK_URL", "https://hooks.example.com/sardis")
    client = Sardis(api_key=api_key)

    print("=" * 60)
    print("Sardis Webhook Subscription Lifecycle")
    print("=" * 60)

    # 1. What events can we subscribe to?
    event_types = client.webhooks.list_event_types()
    print(f"\n{len(event_types)} event types available:")
    for et in event_types:
        print(f"  - {et}")

    # 2. Create a subscription.
    print(f"\nCreating subscription -> {receiver_url}")
    webhook = client.webhooks.create(
        url=receiver_url,
        events=event_types,  # subscribe to everything for the demo
        description="event_webhooks.py example",
    )
    print(f"  id:     {webhook.webhook_id}")
    print(f"  active: {webhook.is_active}")

    # 3. Rotate the signing secret (returns the new secret to store securely).
    print("\nRotating signing secret...")
    rotated = client.webhooks.rotate_secret(webhook.webhook_id)
    secret = rotated.get("secret") or rotated.get("signing_secret")
    print(f"  new secret: {'<received, store securely>' if secret else rotated}")

    # 4. Fire a test delivery and inspect it.
    print("\nSending a test delivery...")
    delivery = client.webhooks.test(webhook.webhook_id)
    print(f"  delivery:    {delivery.delivery_id}")
    print(f"  status_code: {delivery.status_code}")
    print(f"  success:     {delivery.success}")

    # 5. List recent deliveries.
    print("\nRecent deliveries:")
    for d in client.webhooks.list_deliveries(webhook.webhook_id):
        print(f"  {d.event_type:<24} -> {d.status_code} (ok={d.success})")

    print()
    _demo_signature_roundtrip()

    print("\nTo stop receiving events: client.webhooks.delete(webhook_id)")


if __name__ == "__main__":
    print()
    print("Sardis Webhooks Example")
    print("=" * 60)
    main()
