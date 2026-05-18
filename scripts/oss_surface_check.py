#!/usr/bin/env python3
"""Fail if private/company material is tracked in the public OSS repo."""

from __future__ import annotations

import subprocess
import sys


BLOCKED_PREFIXES = (
    "apps/dashboard/",
    "docs/audits/evidence/",
    "docs/cdp/",
    "docs/compliance/",
    "docs/gtm/",
    "docs/hiring/",
    "docs/investor/",
    "docs/ops/",
    "docs/outbound/",
    "docs/outreach/",
    "docs/partnerships/",
    "docs/runbooks/",
    "docs/sales/",
    "docs/superpowers/",
    "docs/compliance/soc2/",
    "docs/yc/",
    "packages/sardis-checkout-ui/",
    "packages/ui-web/",
    "scripts/gtm/",
    "scripts/investor",
    "scripts/outreach/",
)

BLOCKED_FILES = {
    "docs/business-plan.md",
    "docs/DEPLOYMENT-GUIDE-V2.md",
    "docs/investor-list.xlsx",
    "docs/investor-proof-memo-march-2026.md",
    "docs/PRODUCTION_DEPLOYMENT.md",
    "docs/production-runbook.md",
    "docs/operations/dual-track-deployment.md",
    "docs/audits/claims-evidence.md",
    "docs/audits/control-testing-cadence-q1-2026.md",
    "docs/audits/final-remediation-report.md",
    "docs/audits/prelaunch-remediation-plan.md",
    "scripts/check_design_partner_readiness.py",
    "scripts/bootstrap_staging_api_key.sh",
    "scripts/check_demo_deploy_readiness.sh",
    "scripts/demo-mainnet-e2e.py",
    "scripts/deploy-cloudrun.sh",
    "scripts/deploy-demo-testnet.sh",
    "scripts/deploy-mainnet-contracts.sh",
    "scripts/deploy-mainnet.sh",
    "scripts/deploy-sardis-connect.sh",
    "scripts/deploy_gcp_cloudrun_staging.sh",
    "scripts/generate_phase2_targets.mjs",
    "scripts/generate_staging_secrets.sh",
    "scripts/health_monitor.sh",
    "scripts/monitor_contracts.sh",
    "scripts/onboard_partner.sh",
    "scripts/setup-monitoring.sh",
    "scripts/setup-production.sh",
    "scripts/submit_ecosystem_prs.sh",
    "scripts/verify-mainnet.sh",
    "scripts/yc_wow_demo.py",
    "scripts/release/compliance_execution_check.sh",
    "scripts/release/demo_proof_assets_check.sh",
    "scripts/release/demo_proof_check.sh",
    "scripts/release/drill_metrics_check.sh",
    "scripts/release/ga_prep_check.sh",
    "scripts/release/generate_enterprise_ga_readiness_artifact.py",
    "scripts/release/generate_ops_readiness_evidence.py",
    "scripts/release/generate_provider_live_lane_artifact.py",
    "scripts/release/generate_soc2_evidence_manifest.py",
    "scripts/release/issuer_compliance_pack_check.sh",
    "scripts/release/mainnet_ops_drill_check.sh",
    "scripts/release/ops_readiness_check.sh",
    "scripts/release/provider_live_lane_cert_check.sh",
    "scripts/release/smart_contract_audit_check.sh",
    "scripts/release/validate_drill_metrics.py",
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    blocked: list[str] = []
    for path in tracked_files():
        if path in BLOCKED_FILES or path.startswith(BLOCKED_PREFIXES):
            blocked.append(path)

    if blocked:
        print("Private/company material is tracked in the public OSS repo:")
        for path in blocked:
            print(f"  - {path}")
        print("\nMove these files to a private repository or add a public-safe replacement.")
        return 1

    print("OSS surface check passed: no blocked private/company paths are tracked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
