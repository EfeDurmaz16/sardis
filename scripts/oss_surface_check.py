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

BLOCKED_TEXT_SNIPPETS = {
    "You can now start the API and dashboard!": (
        "Public demo tooling must not direct contributors to the private "
        "hosted dashboard surface."
    ),
    "cd dashboard && pnpm dev": (
        "Public contributor instructions must not point to the private hosted "
        "dashboard source tree."
    ),
    "cd landing && pnpm dev": (
        "Public contributor instructions must use apps/landing via root package scripts."
    ),
    "├── dashboard/": (
        "Tracked public repo maps must not present the removed private dashboard "
        "as part of the OSS source layout."
    ),
    "│   ├── api/": (
        "Tracked public repo maps must use packages/reference-api, not the old "
        "generic API package."
    ),
    "https://app.sardis.sh/transactions": (
        "Public CLI demo receipts must point contributors to local evidence "
        "inspection or public docs, not the private hosted product."
    ),
    "Open dashboard": (
        "Public CLI demo next steps must not route contributors into the private "
        "hosted product surface."
    ),
    "https://dashboard.sardis.sh/api-keys": (
        "Public SDK and docs onboarding must describe self-hosted/reference API "
        "key setup instead of private hosted dashboard key management."
    ),
    "https://dashboard.sardis.sh/signup": (
        "Public SDK and docs onboarding must not route contributors into private "
        "hosted product signup."
    ),
}

BLOCKED_UPTIME_URLS = {
    "https://dashboard.sardis.sh": "hosted dashboard uptime belongs in the private product repo",
    "https://checkout.sardis.sh": "hosted checkout uptime belongs in the private product repo",
}

TEXT_FILE_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".ts",
    ".tsx",
    ".js",
    ".json",
    ".yaml",
    ".yml",
}

TEXT_SNIPPET_SCAN_EXCLUDED_FILES = {
    "scripts/oss_surface_check.py",
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
    tracked = tracked_files()
    blocked: list[str] = []
    blocked_text: list[tuple[str, str, str]] = []
    blocked_uptime_urls: list[tuple[str, str]] = []
    for path in tracked:
        if path in BLOCKED_FILES or path.startswith(BLOCKED_PREFIXES):
            blocked.append(path)
            continue
        if path in TEXT_SNIPPET_SCAN_EXCLUDED_FILES:
            continue
        if not any(path.endswith(suffix) for suffix in TEXT_FILE_SUFFIXES):
            continue
        try:
            with open(path, encoding="utf-8") as file:
                text = file.read()
        except UnicodeDecodeError:
            continue
        for snippet, reason in BLOCKED_TEXT_SNIPPETS.items():
            if snippet in text:
                blocked_text.append((path, snippet, reason))

    uptime_config = ".upptimerc.yml"
    if uptime_config in tracked:
        with open(uptime_config, encoding="utf-8") as file:
            text = file.read()
        for url, reason in BLOCKED_UPTIME_URLS.items():
            if url in text:
                blocked_uptime_urls.append((url, reason))

    if blocked or blocked_text or blocked_uptime_urls:
        print("Private/company material is tracked in the public OSS repo:")
        for path in blocked:
            print(f"  - {path}")
        for path, snippet, reason in blocked_text:
            print(f"  - {path}: {snippet!r} ({reason})")
        for url, reason in blocked_uptime_urls:
            print(f"  - {uptime_config}: {url} ({reason})")
        print("\nMove these files to a private repository or add a public-safe replacement.")
        return 1

    print("OSS surface check passed: no blocked private/company paths are tracked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
