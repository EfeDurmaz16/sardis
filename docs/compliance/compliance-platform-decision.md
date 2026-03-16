# Compliance Platform Decision

**Date:** March 2026
**Decision:** Start with DSALTA (free Year 1), fallback to Sprinto ($4K/yr)

## Platforms Evaluated

| Platform | Price (Year 1) | SOC 2 | GDPR | PCI | AI Features | Verdict |
|----------|---------------|-------|------|-----|-------------|---------|
| DSALTA | **Free** | Yes | Yes | Yes | AI-native | **Primary choice** |
| Sprinto | ~$4,000 | Yes | Yes | Yes | 90% automation | **Fallback** |
| Delve (YC W24) | Unknown | Yes | Yes | Yes | AI agents, ISO 42001 | Worth exploring |
| Vanta | ~$10,000 | Yes | Yes | Yes | AI policy gen | Too expensive pre-revenue |
| Drata | ~$7,500 | Yes | Yes | Yes | Compliance-as-Code | Too expensive pre-revenue |
| Secureframe | ~$8,000 | Yes | Yes | Yes | 300+ integrations | Too expensive pre-revenue |
| Thoropass | ~$14,500 | Yes | Yes | Yes | Bundled audit | Too expensive pre-revenue |
| Duna | N/A | No | No | No | KYB only | Not relevant (KYB, not SOC 2) |

## Why DSALTA

1. Free Year 1 including audit — critical for pre-revenue startup
2. AI-native platform — generates policies in hours, not weeks
3. Built for startups — not a scaled-down enterprise tool
4. 50% off Year 2 — gradual cost ramp

## Known Gap: No Cloud Run or Neon Support

All platforms lack native GCP Cloud Run and Neon PostgreSQL monitoring. Manual evidence needed:
- Cloud Run: IAM policies, deploy configs, network settings (from GCP console)
- Neon: encryption docs, access controls, backup policies (from Neon dashboard)

## PCI DSS: Not Needed Yet

Stripe handles card data → SAQ-A self-assessment sufficient (not full PCI audit). Add PCI framework to compliance tool when Stripe Issuing goes production.

## Timeline

| Week | Action |
|------|--------|
| 1 | Sign up for DSALTA, connect GCP + GitHub |
| 1-2 | AI generates policies, review and customize |
| 2-3 | Remediate gaps (access reviews, incident response) |
| 3 | Start SOC 2 Type II observation period (3-month minimum) |
| 3-14 | Observation period with continuous monitoring |
| 15-17 | Auditor review → Type II report issued |

**Shortcut:** Get Type I first (2-4 weeks) to unblock enterprise conversations, then run Type II observation in parallel.

## Action Items

- [ ] Sign up for DSALTA (dsalta.com) — free
- [ ] Connect GCP project
- [ ] Connect GitHub organization
- [ ] Review AI-generated security policies
- [ ] Prepare manual evidence for Cloud Run and Neon
- [ ] Schedule Type I audit start
