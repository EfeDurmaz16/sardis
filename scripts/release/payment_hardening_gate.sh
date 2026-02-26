#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[payment-hardening-gate] validating payment hardening controls"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[payment-hardening-gate][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[payment-hardening-gate][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

if ! command -v rg >/dev/null 2>&1; then
  echo "[payment-hardening-gate][fail] rg command is required"
  exit 1
fi

require_file "docs/design-partner/payment-hardening-preprod-gate.md"
require_file "docs/design-partner/payment-hardening-slo-alerts.md"
require_file "docs/design-partner/pci-approvals-and-db-hardening-checklist.md"
require_file "docs/design-partner/pan-boundary-provider-matrix.md"

require_match 'policy_pin_requires_active_policy' \
  'packages/sardis-api/src/sardis_api/routers/onchain_payments.py' \
  'on-chain policy pin fail-closed guard must be present'
require_match 'policy_pin_attestation_unavailable' \
  'packages/sardis-api/src/sardis_api/routers/onchain_payments.py' \
  'on-chain policy attestation fail-closed guard must be present'
require_match 'PROMPT_INJECTION_PATTERNS' \
  'packages/sardis-api/src/sardis_api/routers/onchain_payments.py' \
  'on-chain prompt injection patterns must be defined'
require_match '_goal_drift_block_threshold' \
  'packages/sardis-api/src/sardis_api/routers/onchain_payments.py' \
  'on-chain goal drift block threshold guard must be present'
require_match '_signed_policy_snapshot_required' \
  'packages/sardis-api/src/sardis_api/routers/onchain_payments.py' \
  'on-chain signed policy snapshot requirement guard must be present'

require_match 'cursor_scope_mismatch' \
  'packages/sardis-api/src/sardis_api/routers/compliance.py' \
  'evidence export cursor scope binding must be enforced'
require_match 'Opaque replay-safe pagination cursor' \
  'packages/sardis-api/src/sardis_api/routers/compliance.py' \
  'evidence export must expose replay-safe cursor API'

require_match 'card_details_invalid' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout must reject invalid revealed card details'
require_match '_sanitize_audit_payload' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout audit payload redaction must be present'
require_match '_pan_executor_runtime_ready' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout PAN runtime readiness gate must be present'
require_match '_pan_provider_boundary_matrix' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout must support provider boundary matrix'
require_match '_resolve_pan_boundary_mode' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout must resolve effective pan boundary mode deterministically'
require_match 'pan_provider_profile_disallows_pan_entry' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout must expose provider profile lock reason'
require_match '_require_shared_secret_store' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout must fail-closed without shared secret store in production'
require_match '_required_checkout_approvals' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout must compute approval quorum requirements deterministically'
require_match '_checkout_signed_policy_snapshot_required' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout signed policy snapshot guard must be present'
require_match 'policy_snapshot_signer_not_configured' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout must fail closed when signed policy snapshot is required but signer is missing'
require_match 'approval_distinct_reviewer_quorum_not_met' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout must enforce distinct reviewer quorum when configured'
require_match '_security_incident_severity' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout incident severity taxonomy must be present'
require_match '/secure/security-policy' \
  'packages/sardis-api/src/sardis_api/routers/secure_checkout.py' \
  'secure checkout security-policy visibility endpoint must be present'
require_match '_check_a2a_trust_relation' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A trust table enforcement must be present'
require_match '_append_a2a_trust_audit_entry' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A trust relation mutations must be audit logged'
require_match '_validate_trust_mutation_approval' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A trust relation mutations must enforce approval validation'
require_match '_required_trust_mutation_approvals' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A trust relation mutations must support approval quorum controls'
require_match '/trust/peers' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A peer discovery endpoint must be present'
require_match 'include_wallet_addresses' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A peer discovery must support optional wallet address directory visibility'
require_match 'broadcast_targets' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A peer discovery must expose trusted broadcast targets'
require_match '/trust/audit/recent' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A trust audit visibility endpoint must be present'
require_match '/trust/security-policy' \
  'packages/sardis-api/src/sardis_api/routers/a2a.py' \
  'A2A security policy visibility endpoint must be present'
require_match 'SARDIS_ASA_FAIL_CLOSED_ON_CARD_LOOKUP_ERROR' \
  'packages/sardis-cards/src/sardis_cards/webhooks.py' \
  'ASA card lookup error fail-closed toggle must be present'
require_match '/asa/security-policy' \
  'packages/sardis-api/src/sardis_api/routers/cards.py' \
  'cards router must expose ASA security policy visibility endpoint'

require_match 'test_onchain_payment_adversarial_prompt_patterns_require_approval' \
  'packages/sardis-api/tests/test_onchain_payments.py' \
  'adversarial on-chain prompt test must exist'
require_match 'test_onchain_payment_goal_drift_review_returns_pending_approval' \
  'packages/sardis-api/tests/test_onchain_payments.py' \
  'on-chain goal drift review path must be test covered'
require_match 'test_topup_all_providers_failed_returns_502_and_records_attempts' \
  'packages/sardis-api/tests/test_stripe_funding.py' \
  'funding all-failed chaos test must exist'
require_match 'test_pan_entry_execute_fail_closed_on_invalid_revealed_card_details' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'PAN invalid reveal fail-closed test must exist'
require_match 'test_security_incident_emits_severity_and_ops_approval_pending' \
  'packages/sardis-api/tests/test_secure_checkout_risk_response.py' \
  'secure checkout risk response taxonomy test must exist'
require_match 'test_security_policy_endpoint_returns_runtime_guardrails' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'secure checkout security-policy endpoint test must exist'
require_match 'test_pan_entry_quorum_requires_two_approvals_when_configured' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'secure checkout approval quorum behavior must be test covered'
require_match 'test_pan_entry_quorum_requires_distinct_reviewers' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'secure checkout distinct reviewer quorum must be test covered'
require_match 'test_prod_provider_profile_locks_boundary_mode_for_stripe' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'secure checkout provider profile lock must be test covered'
require_match 'test_prod_provider_profile_lithic_defaults_to_hosted_only' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'secure checkout provider profile hosted-only default must be test covered'
require_match 'test_prod_provider_profile_lithic_can_allow_break_glass_with_override' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'secure checkout provider profile override path must be test covered'
require_match 'test_prod_secure_checkout_requires_policy_snapshot_signer' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'secure checkout prod signed snapshot requirement must be test covered'
require_match 'test_secure_checkout_evidence_includes_signed_policy_snapshot_when_configured' \
  'packages/sardis-api/tests/test_secure_checkout_executor.py' \
  'secure checkout evidence must include signed policy snapshot fields when configured'
require_match 'test_a2a_trust_table_rejects_untrusted_pair' \
  'packages/sardis-api/tests/test_a2a_trust_table.py' \
  'A2A trust table rejection test must exist'
require_match 'test_ensure_table_prod_requires_migration' \
  'packages/sardis-api/tests/test_a2a_trust_repository.py' \
  'A2A trust repository must fail closed in production when table is missing'
require_match 'test_trust_peers_returns_only_trusted_by_default' \
  'packages/sardis-api/tests/test_a2a_trust_endpoints.py' \
  'A2A peer discovery endpoint must be test covered'
require_match 'test_trust_peers_can_include_wallet_addresses_and_broadcast_targets' \
  'packages/sardis-api/tests/test_a2a_trust_endpoints.py' \
  'A2A wallet-aware peer directory must be test covered'
require_match 'provider == \"a2a_trust\"' \
  'packages/sardis-api/tests/test_a2a_trust_endpoints.py' \
  'A2A trust relation audit trail must be test covered'
require_match 'test_admin_can_list_recent_a2a_trust_audit_entries' \
  'packages/sardis-api/tests/test_a2a_trust_endpoints.py' \
  'A2A trust audit visibility endpoint must be test covered'
require_match 'test_admin_can_view_a2a_security_policy' \
  'packages/sardis-api/tests/test_a2a_trust_endpoints.py' \
  'A2A security policy visibility endpoint must be test covered'
require_match 'test_trust_relation_mutation_requires_approval_when_enabled' \
  'packages/sardis-api/tests/test_a2a_trust_endpoints.py' \
  'A2A trust approval enforcement must be test covered'
require_match 'test_trust_relation_mutation_quorum_requires_two_distinct_reviewers' \
  'packages/sardis-api/tests/test_a2a_trust_endpoints.py' \
  'A2A trust approval quorum must be test covered'
require_match 'test_asa_card_lookup_error_fail_closed_in_production' \
  'packages/sardis-cards/tests/test_asa_handler.py' \
  'ASA fail-closed behavior must be test covered'
require_match 'test_cards_asa_security_policy_endpoint' \
  'packages/sardis-api/tests/test_cards_provider_introspection.py' \
  'ASA security policy endpoint must be test covered'

if [[ "${RUN_PAYMENT_HARDENING_TESTS:-0}" == "1" ]]; then
  if ! command -v pytest >/dev/null 2>&1; then
    echo "[payment-hardening-gate][fail] RUN_PAYMENT_HARDENING_TESTS=1 requires pytest"
    failures=$((failures + 1))
  else
    echo "[payment-hardening-gate] running targeted payment hardening tests"
    if ! pytest -q \
      packages/sardis-api/tests/test_onchain_payments.py \
      packages/sardis-api/tests/test_compliance_audit_api.py \
      packages/sardis-api/tests/test_secure_checkout_executor.py \
      packages/sardis-api/tests/test_secure_checkout_risk_response.py \
      packages/sardis-api/tests/test_a2a_trust_table.py \
      packages/sardis-api/tests/test_a2a_trust_endpoints.py \
      packages/sardis-api/tests/test_a2a_trust_repository.py \
      packages/sardis-api/tests/test_stripe_funding.py \
      packages/sardis-api/tests/test_cards_provider_introspection.py \
      packages/sardis-cards/tests/test_asa_handler.py; then
      failures=$((failures + 1))
    fi
  fi
else
  echo "[payment-hardening-gate] skipping tests (set RUN_PAYMENT_HARDENING_TESTS=1 to enable)"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[payment-hardening-gate] completed with $failures failure(s)"
  exit 1
fi

echo "[payment-hardening-gate] pass"
