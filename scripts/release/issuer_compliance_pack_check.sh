#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[issuer-compliance-pack] validating warm-issuing compliance assets"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[issuer-compliance-pack][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[issuer-compliance-pack][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_file "docs/design-partner/compliance-pack/README.md"
require_file "docs/design-partner/compliance-pack/disclosures-and-agreements.md"
require_file "docs/design-partner/compliance-pack/complaints-disputes-sop.md"
require_file "docs/design-partner/compliance-pack/receipts-recordkeeping.md"
require_file "docs/design-partner/compliance-pack/support-evidence-checklist.md"
require_file "docs/design-partner/cpn-warm-issuing-30-day-plan.md"

require_match 'Stripe-hosted onboarding|hosted onboarding' \
  docs/design-partner/compliance-pack/disclosures-and-agreements.md \
  "disclosures checklist must include hosted onboarding strategy"
require_match 'complaint|dispute' \
  docs/design-partner/compliance-pack/complaints-disputes-sop.md \
  "complaints/disputes SOP must define complaint + dispute flow"
require_match 'receipt|record' \
  docs/design-partner/compliance-pack/receipts-recordkeeping.md \
  "receipts/recordkeeping doc must include receipt retention controls"
require_match 'SARDIS_ISSUING_LIVE_ENABLED' \
  docs/design-partner/compliance-pack/support-evidence-checklist.md \
  "support evidence checklist must reference warm-mode live toggle control"
require_match 'Week 1|Week 2|Week 3|Week 4' \
  docs/design-partner/cpn-warm-issuing-30-day-plan.md \
  "30-day plan must include weekly execution milestones"
require_match 'SARDIS_ISSUING_LIVE_ENABLED' \
  packages/sardis-api/src/sardis_api/routers/cards.py \
  "cards router must enforce explicit issuing live toggle"

if [[ "$failures" -gt 0 ]]; then
  echo "[issuer-compliance-pack] completed with $failures failure(s)"
  exit 1
fi

echo "[issuer-compliance-pack] pass"

