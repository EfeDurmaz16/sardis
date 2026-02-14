# Webhook Conformance Runbook

## Scope
This runbook validates webhook security controls before release:
- Signature verification
- Replay protection
- Idempotency behavior
- Secret-handling paths

## Command
Run from repo root:

```bash
bash scripts/release/webhook_conformance_check.sh
```

## Included Tests
- `packages/sardis-api/tests/test_middleware_security.py`
- `tests/test_checkout_webhook_security.py`
- `tests/test_webhooks.py`
- `tests/test_audit_f12_replay_cache.py`

## Expected Result
- Script exits `0`
- No failed tests
- Skips are acceptable where tests are explicitly environment-gated

## Release Gate Integration
- `scripts/release/readiness_check.sh` runs this check.
- `.github/workflows/deploy.yml` validate job runs this check before any deploy job.

## If It Fails
1. Re-run the failing test directly with `pytest -q <file>::<test_name>`.
2. Fix signature/replay/idempotency logic.
3. Re-run `bash scripts/release/webhook_conformance_check.sh`.
4. Do not proceed with deployment until it passes.

## Secret Rotation Procedure
1. Rotate the webhook secret using the API endpoint:
```bash
curl -X POST "https://api.sardis.sh/api/v2/webhooks/<subscription_id>/rotate-secret" \
  -H "X-API-Key: <admin_or_service_api_key>"
```
2. Update downstream receiver configuration with the new secret.
3. Send a signed test delivery and verify `2xx` from receiver.
4. Confirm old secret is no longer accepted.
