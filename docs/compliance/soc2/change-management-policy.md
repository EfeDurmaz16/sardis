# Change Management Policy

**Document ID:** SARDIS-SOC2-CMP-001
**Version:** 1.0
**Effective Date:** 2026-03-10
**Last Reviewed:** 2026-03-10
**Owner:** Engineering
**Classification:** Internal

---

## 1. Purpose

This policy defines the requirements for managing changes to the Sardis platform, including code, configuration, infrastructure, and database schema. It ensures all changes are reviewed, tested, approved, and auditable, in compliance with SOC 2 Trust Service Criteria CC8.1 (change management).

## 2. Scope

This policy applies to all changes to:

- Application source code (all packages under `packages/`, `contracts/`, `sardis/`)
- Infrastructure configuration (Cloud Run, Vercel, Neon, Upstash)
- Database schema (SQL migrations in `packages/sardis-api/migrations/`)
- Smart contracts (Solidity contracts in `contracts/src/`)
- CI/CD pipelines (`.github/workflows/`)
- Environment variables and secrets
- Third-party service configurations (Turnkey, Stripe, iDenfy, Elliptic)

## 3. Change Categories

### 3.1 Standard Change

Routine changes that follow the normal development workflow. Examples:

- Feature additions
- Bug fixes
- Dependency updates
- Documentation updates
- Non-breaking API enhancements

### 3.2 Security-Sensitive Change

Changes that affect authentication, authorization, cryptographic operations, financial transactions, or compliance. Examples:

- Modifications to `packages/sardis-api/src/sardis_api/authz.py` (auth/authz)
- Changes to `packages/sardis-core/src/sardis_v2_core/spending_policy.py` (policy engine)
- Changes to `packages/sardis-api/src/sardis_api/routers/emergency.py` (emergency controls)
- Changes to `packages/sardis-api/src/sardis_api/kill_switch_dep.py` (kill switch)
- Smart contract modifications (`contracts/src/`)
- Webhook signature verification logic
- MPC/wallet key management (`packages/sardis-wallet/`)
- Compliance engine (`packages/sardis-compliance/`)
- Database migration files affecting financial data

### 3.3 Emergency Change (Hotfix)

Changes required to resolve a production incident with active customer impact. See Section 9.

### 3.4 Infrastructure Change

Changes to deployment configuration, cloud resources, or third-party service settings. Examples:

- Cloud Run service configuration
- Vercel project settings
- Neon database scaling
- DNS changes

## 4. Pull Request Requirements

### 4.1 Standard Changes

| Requirement | Detail |
|-------------|--------|
| **Minimum Approvals** | 1 code review approval |
| **Reviewer Qualifications** | Any team member with write access to the repository |
| **CI Checks (must pass)** | All checks listed in Section 5 |
| **Branch Protection** | `main` branch is protected; direct push is prohibited |
| **Merge Method** | Squash merge preferred; merge commit allowed for multi-commit PRs |

### 4.2 Security-Sensitive Changes

| Requirement | Detail |
|-------------|--------|
| **Minimum Approvals** | 2 code review approvals |
| **Reviewer Qualifications** | At least 1 reviewer must be a senior engineer or security team member |
| **Additional Review** | Security-sensitive files trigger automatic CODEOWNERS review request |
| **CI Checks (must pass)** | All checks listed in Section 5, plus gitleaks secret scan |
| **Threat Assessment** | PR description must include a security impact assessment |

### 4.3 Smart Contract Changes

| Requirement | Detail |
|-------------|--------|
| **Minimum Approvals** | 2 code review approvals |
| **Reviewer Qualifications** | At least 1 reviewer must have Solidity/smart contract experience |
| **CI Checks** | `forge fmt --check`, `forge build --sizes`, `forge test -vvv`, gas ceiling tests |
| **Audit Requirement** | Material contract changes require external audit before mainnet deployment |
| **Testnet Verification** | All contract changes must be deployed and tested on testnet (Base Sepolia) before mainnet |

## 5. Continuous Integration Checks

All pull requests to the `main` branch must pass the following CI pipeline (defined in `.github/workflows/ci.yml`):

### 5.1 Python Lint and Test

| Check | Tool | Command |
|-------|------|---------|
| Linting | ruff | `uv run ruff check .` |
| Unit tests (root) | pytest | `uv run pytest tests/ -v --tb=short` |
| Unit tests (packages) | pytest | `uv run pytest packages/sardis-core/tests/ packages/sardis-ledger/tests/ -v --tb=short` |
| Idempotency E2E | custom | `bash scripts/release/idempotency_replay_e2e_check.sh` |

### 5.2 Smart Contract Checks

| Check | Tool | Command |
|-------|------|---------|
| Formatting | forge fmt | `forge fmt --check` |
| Build | forge build | `forge build --sizes -vv` |
| Tests | forge test | `forge test -vvv` |
| Gas ceilings | forge test | `forge test --match-test "testGasCeiling_" --gas-report -vv` |

### 5.3 TypeScript SDK

| Check | Tool | Command |
|-------|------|---------|
| Build SDK | pnpm | `pnpm --filter @sardis/sdk-js build` |
| Build MCP Server | pnpm | `pnpm --filter @sardis/mcp-server build` |
| Type check | tsc | `pnpm --filter @sardis/sdk-js tsc --noEmit` |

### 5.4 Frontend Builds

| Check | Component | Command |
|-------|-----------|---------|
| Dashboard | React + Vite | `cd dashboard && pnpm build` |
| Landing page | React + Vite | `cd landing && pnpm build` |

### 5.5 Secret Scanning

| Check | Tool | Trigger |
|-------|------|---------|
| Gitleaks | gitleaks-action v2 | Every push and PR to `main` (`.github/workflows/secret-scan.yml`) |

A gitleaks finding blocks the PR from merging.

## 6. Deployment Process

### 6.1 Standard Deployment Flow

```
Developer branch → Pull Request → CI checks → Code review → Merge to main
                                                                    ↓
                                                            Staging deploy
                                                                    ↓
                                                            Staging validation
                                                                    ↓
                                                            Production deploy
                                                                    ↓
                                                            Health check verification
```

### 6.2 Staging Deployment

Triggered via the Deploy workflow (`.github/workflows/deploy.yml`):

1. **Validate:** Release gates run (webhook conformance check, dependency installation)
2. **Migrate:** Database migrations run against staging (`alembic upgrade head`)
3. **Deploy:** Vercel deployment with `SARDIS_ENVIRONMENT=staging`
4. **Health check:** `curl -f https://api-staging.sardis.sh/api/v2/health`
5. **Smoke test:** Manual verification of critical paths (authentication, payment simulation, webhook delivery)

### 6.3 Production Deployment

Production deployment requires:

1. **Successful staging deployment** — production cannot be deployed without prior staging validation
2. **All required secrets verified** — deploy job checks for `PRODUCTION_DATABASE_URL`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`
3. **Database migrations** run against production
4. **Vercel production deploy** with `--prod` flag
5. **Post-deploy health check:** `curl -f https://api.sardis.sh/api/v2/health`

### 6.4 Deployment Environments

| Environment | URL | Purpose |
|-------------|-----|---------|
| Staging API | `https://api-staging.sardis.sh` | Pre-production validation |
| Production API | `https://api.sardis.sh` | Live traffic |
| Staging Dashboard | `https://dashboard-staging.sardis.sh` | UI testing |
| Production Dashboard | `https://app.sardis.sh` | Live dashboard |
| Staging Landing | `https://staging.sardis.sh` | Marketing site testing |
| Production Landing | `https://sardis.sh` | Live marketing site |

## 7. Rollback Procedures

### 7.1 Application Rollback

1. **Identify the last known good deployment** via Vercel dashboard or `git log`
2. **Redeploy the previous version:**
   ```bash
   # Via GitHub Actions Deploy workflow
   # Set version input to the previous release tag/commit
   ```
   Or via Vercel dashboard: promote the previous deployment to production.
3. **Verify:** Health check must return `"status": "healthy"`
4. **If database migration was applied:**
   - Check if the migration has a corresponding downgrade (`alembic downgrade -1`)
   - If no downgrade is available, assess whether the schema change is backward-compatible
   - Forward-only migrations require deploying a fix rather than rolling back

### 7.2 Smart Contract Rollback

Smart contracts are immutable once deployed. Rollback strategies:

1. **Proxy contracts:** Deploy a new implementation and update the proxy pointer
2. **Kill switch:** Pause the contract via the admin function
3. **Migration:** Deploy a new contract version and migrate state

### 7.3 Infrastructure Rollback

- **Cloud Run:** Revert to previous revision via `gcloud run services update-traffic`
- **Vercel:** Promote previous deployment via Vercel dashboard
- **Database:** Neon point-in-time restore (see Disaster Recovery Runbook)

## 8. Database Migration Requirements

All SQL migrations (`packages/sardis-api/migrations/`) must:

1. Be reviewed as part of the PR process
2. Include a descriptive filename (e.g., `064_emergency_freeze.sql`)
3. Be idempotent where possible (use `IF NOT EXISTS`, `IF EXISTS`)
4. Include rollback SQL in comments or a companion downgrade file
5. Be tested on staging before production
6. Not drop columns or tables without a deprecation period (minimum 30 days)
7. Not hold locks for extended periods (avoid `ALTER TABLE` on large tables during peak traffic)

## 9. Emergency Hotfix Process

When a production incident requires an immediate code change:

### 9.1 Authorization

- Any on-call engineer can initiate an emergency hotfix
- A second engineer must review the change (pair programming or rapid code review)
- Post-merge retrospective review is required within 24 hours

### 9.2 Procedure

1. **Create hotfix branch** from `main`:
   ```
   git checkout -b hotfix/<issue-description> main
   ```
2. **Implement minimal fix** — address only the incident; no unrelated changes
3. **Create PR** with `[HOTFIX]` prefix in the title
4. **Fast-track review:** 1 approval minimum (reviewer should be on-call or senior engineer)
5. **CI checks must still pass** — no bypassing CI for hotfixes
6. **Deploy to staging** and verify the fix resolves the issue
7. **Deploy to production**
8. **Post-deploy verification:**
   - Health check: `GET /health`
   - Verify the specific incident is resolved
   - Monitor error rates for 30 minutes

### 9.3 Post-Hotfix Requirements

Within 24 hours of a hotfix:

- [ ] Incident report filed (see Incident Response Plan)
- [ ] Full code review completed (if abbreviated during hotfix)
- [ ] Regression test added for the failure scenario
- [ ] Root cause analysis documented
- [ ] Follow-up ticket created for any technical debt introduced

## 10. Configuration Changes

Changes to environment variables and feature flags:

1. **Documented in PR** or change request (even if no code change)
2. **Applied via `--update-env-vars`** (never `--set-env-vars` which wipes all variables)
3. **Verified via health check** after application
4. **Logged in audit trail** — Cloud Run deployment logs and audit log

## 11. Third-Party Service Changes

Changes to third-party service configurations (Turnkey, Stripe, iDenfy, Elliptic, Neon, Upstash):

1. **Documented** in a change request with justification
2. **Tested in staging/sandbox** before production
3. **Credentials rotated** per the Secrets Rotation Runbook if access patterns change
4. **Monitored** via health check component status after the change

## 12. Audit Trail

All changes are traceable through:

- **Git history:** Every code change is a commit with author, timestamp, and message
- **PR reviews:** GitHub preserves review comments, approvals, and CI results
- **Deployment logs:** GitHub Actions workflow runs are retained
- **Admin audit log:** `log_admin_action` records all administrative operations
- **Emergency events:** `emergency_freeze_events` table with full event history

## 13. Review Cadence

This policy is reviewed:

- **Annually** as part of the SOC 2 audit cycle
- **After any incident** where change management was a contributing factor
- **Upon material changes** to the development or deployment process

---

**Appendix A: Related Documents**

- Incident Response Plan (`docs/compliance/soc2/incident-response-plan.md`)
- Secrets Rotation Runbook (`docs/compliance/soc2/secrets-rotation-runbook.md`)
- Evidence Matrix (`docs/compliance/soc2/evidence-matrix.md`)

**Appendix B: CI/CD Pipeline Files**

- `.github/workflows/ci.yml` — Main CI pipeline
- `.github/workflows/secret-scan.yml` — Gitleaks secret scanning
- `.github/workflows/deploy.yml` — Deployment workflow
- `.github/workflows/ci-integrations.yml` — Integration test pipeline
- `.github/workflows/release-python-sdk.yml` — Python SDK release
