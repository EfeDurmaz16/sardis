# Private Repository Migration Manifest

This file records tracked public-repo paths that should move to a private company or product repository instead of remaining in Sardis OSS.

The public repository should not contain private commercial planning, hiring, investor, partnership-development, customer-specific, or GTM workflow material. When the private repository is created, recover these files from git history or a local private archive, then remove them from public history if needed.

## Removed From Public Tracking

The following categories are private by default:

- `docs/audits/evidence/` - generated operational/provider readiness evidence and latest-run artifacts
- `docs/audits/claims-evidence.md`, `docs/audits/control-testing-cadence-q1-2026.md`, `docs/audits/final-remediation-report.md`, `docs/audits/prelaunch-remediation-plan.md` - launch/company readiness evidence and remediation history
- `docs/cdp/` - commercial/customer-development drafts
- `docs/compliance/` - company compliance, FinCEN, SOC2, and incident-response program material
- `docs/compliance/soc2/` - company-specific compliance policies, runbooks, and audit-readiness material
- `docs/DEPLOYMENT-GUIDE-V2.md`, `docs/PRODUCTION_DEPLOYMENT.md`, `docs/production-runbook.md`, `docs/operations/dual-track-deployment.md` - hosted Sardis production deployment and design-partner operations
- `docs/gtm/` - GTM planning and execution material
- `docs/hiring/` - internal hiring materials
- `docs/investor/` - investor decks, diligence reports, and internal fundraising material
- `docs/ops/` - company-specific operational status and environment audit material
- `docs/outbound/` - outbound targeting, prospecting, and campaign material
- `docs/outreach/` - private outreach drafts and applications
- `docs/partnerships/` - partner-development and LOI drafts
- `docs/runbooks/` - hosted production runbooks unless rewritten as generic public templates
- `docs/sales/` - sales prospecting and outreach strategy
- `docs/superpowers/` - local/internal agent operating plans
- `docs/yc/` - accelerator application drafts
- `api/*/*.json` - generated uptime and response-time snapshots
- `contracts/broadcast/` - generated Foundry broadcast/deployment artifacts
- `scripts/check_design_partner_readiness.py`, `scripts/investor_demo_flow.py`, and private release gates under `scripts/release/` - design-partner, investor-demo, provider certification, SOC2, ops-readiness, formal audit evidence, and GA-prep automation
- `scripts/gtm/` - GTM automation and lead workflow scripts

## Follow-Up

After this branch lands:

1. Create `sardis-product` or `sardis-company-private`.
2. Export these paths from the last pre-removal commit if they are needed.
3. Keep the public repo clean by enforcing the boundary in review.
4. If any removed material was already pushed to a public remote and is truly sensitive, perform a history rewrite with maintainer approval.
