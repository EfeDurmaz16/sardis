#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[provider-cert] validating required artifacts"

required=(
  "docs/design-partner/provider-meeting-kit-stripe-rain-15min.md"
  "docs/design-partner/provider-pre-report-web-q1-2026.md"
  "docs/design-partner/provider-live-lane-certification-scorecard.md"
  "docs/marketing/diligence-response-sheet-stripe-q1-2026.md"
  "docs/marketing/diligence-response-sheet-lithic-q1-2026.md"
  "docs/marketing/diligence-response-sheet-rain-q1-2026.md"
  "docs/marketing/diligence-response-sheet-bridge-q1-2026.md"
)

for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "[provider-cert] missing artifact: $path"
    exit 1
  fi
done

echo "[provider-cert] running provider contract smoke tests"
python3 -m pytest -q \
  packages/sardis-cards/tests/test_provider_contract_matrix.py \
  packages/sardis-api/tests/test_partner_card_webhooks.py::test_partner_webhook_duplicate_event_is_idempotent

echo "[provider-cert] OK"
