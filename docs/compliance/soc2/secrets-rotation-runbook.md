# Secrets Rotation Runbook

**Document ID:** SARDIS-SOC2-SRR-001
**Version:** 1.0
**Effective Date:** 2026-03-10
**Last Reviewed:** 2026-03-10
**Owner:** Engineering / Security
**Classification:** Internal — Restricted

---

## 1. Purpose

This runbook provides step-by-step procedures for rotating all cryptographic secrets, API keys, and credentials used by the Sardis platform. Regular rotation limits the blast radius of any credential compromise and satisfies SOC 2 Trust Service Criteria CC6.1 (logical access security) and CC6.3 (credential management).

## 2. Rotation Schedule

| Secret Type | Rotation Frequency | Grace Period | Owner |
|-------------|-------------------|--------------|-------|
| Sardis API keys (customer-facing) | On demand / on compromise | 24 hours | Engineering |
| Database credentials (Neon) | 90 days | 1 hour | Infrastructure |
| MPC keys (Turnkey) | 180 days / on compromise | Per Turnkey procedure | Security |
| Webhook signing secrets | 90 days | 24 hours | Engineering |
| Stripe API keys | 90 days | 1 hour | Engineering |
| iDenfy API credentials | 90 days | 1 hour | Engineering |
| Elliptic API keys | 90 days | 1 hour | Engineering |
| JWT signing keys | 90 days | 24 hours (dual-key validation) | Security |
| Redis credentials (Upstash) | 90 days | 1 hour | Infrastructure |
| Agent signing keys (Ed25519/ECDSA-P256) | 180 days / on compromise | 24 hours (configurable) | Engineering |

## 3. Pre-Rotation Checklist

Before any rotation:

- [ ] Identify all services and deployments consuming the secret
- [ ] Verify rollback procedure is understood and tested
- [ ] Notify on-call engineer and confirm availability for the rotation window
- [ ] Ensure monitoring dashboards are visible (health endpoint: `GET /health`)
- [ ] Confirm no active incidents or emergency freeze in progress (`GET /api/v2/admin/emergency/status`)
- [ ] Document the rotation in the audit log

## 4. Rotation Procedures

### 4.1 Sardis API Keys (Customer-Facing)

**Context:** API keys are hashed with SHA-256 before storage in the `api_keys` table. The plaintext key is shown to the customer exactly once at creation. Rotation creates a new key and revokes the old one.

**Storage:** PostgreSQL `api_keys` table (SHA-256 hash), environment variable `SARDIS_SECRET_KEY` for HMAC operations.

**Procedure:**

1. **Generate new key:**
   ```
   POST /api/v2/admin/api-keys
   {
     "organization_id": "<org_id>",
     "scopes": ["payments", "wallets"],
     "label": "rotated-<date>"
   }
   ```
2. **Communicate new key** to the customer through the dashboard or secure channel
3. **Set grace period:** Allow 24 hours for the customer to update their integration
4. **Revoke old key:**
   ```
   DELETE /api/v2/admin/api-keys/{old_key_id}
   ```
5. **Verify:** Confirm old key returns 401 on test request
6. **Audit:** Rotation is automatically logged via `log_admin_action` in `packages/sardis-api/src/sardis_api/audit_log.py`

**Rollback:** If the new key is non-functional, re-create the old key hash in the database (requires admin DB access). The old plaintext cannot be recovered — customer must use the new key or request another rotation.

### 4.2 Database Credentials (Neon)

**Context:** PostgreSQL connection credentials managed through Neon console. Used by the API server via `DATABASE_URL` environment variable.

**Storage:** Neon console (primary), Cloud Run environment variables, GitHub Actions secrets.

**Procedure:**

1. **Generate new credentials** in Neon console:
   - Navigate to the project dashboard
   - Go to "Roles" or "Connection Settings"
   - Create a new role or reset the password for the existing role
2. **Update Cloud Run:**
   ```bash
   gcloud run services update sardis-api-staging \
     --update-env-vars "DATABASE_URL=postgresql://new_user:new_pass@ep-xxx.neon.tech/sardis"
   ```
   (Use `--update-env-vars`, never `--set-env-vars` which wipes all variables.)
3. **Update GitHub Actions secrets:**
   - Repository Settings > Secrets and variables > Actions
   - Update `STAGING_DATABASE_URL` and/or `PRODUCTION_DATABASE_URL`
4. **Verify connectivity:**
   ```bash
   curl -f https://api-staging.sardis.sh/health
   ```
   Confirm the `database` component reports `"status": "healthy"` in the deep health check response.
5. **Revoke old credentials** in Neon console after confirming all services are healthy
6. **Repeat for production** after successful staging validation

**Rollback:** Restore the previous password in Neon console, then redeploy with the old `DATABASE_URL`.

### 4.3 MPC Keys (Turnkey)

**Context:** Sardis uses Turnkey for non-custodial MPC wallet management. Private key shares are never held by Sardis. Key rotation involves Turnkey's key rotation API, which re-shares the signing key without changing the wallet address.

**Storage:** Turnkey infrastructure (non-custodial). Sardis stores only `TURNKEY_API_KEY`, `TURNKEY_API_PUBLIC_KEY`, and `TURNKEY_ORGANIZATION_ID` as environment variables.

**Procedure:**

1. **Rotate Turnkey API credentials:**
   - Log in to the Turnkey dashboard
   - Navigate to API Keys under the organization
   - Generate a new API key pair
   - Record the new public key and private key securely
2. **Update environment variables:**
   ```bash
   gcloud run services update sardis-api-staging \
     --update-env-vars "TURNKEY_API_KEY=<new_private_key>,TURNKEY_API_PUBLIC_KEY=<new_public_key>"
   ```
3. **Verify Turnkey connectivity:**
   ```bash
   curl -f https://api-staging.sardis.sh/health
   ```
   Confirm `turnkey` component reports `"status": "healthy"`.
4. **Deactivate old API key** in Turnkey dashboard
5. **For wallet key re-sharing** (advanced, typically only on compromise):
   - Contact Turnkey support for guided key re-sharing procedure
   - This does NOT change wallet addresses — it re-distributes key shares
   - Verify wallet signing capability with a test transaction on testnet

**Rollback:** Reactivate the old API key in Turnkey dashboard and redeploy with old credentials.

### 4.4 Webhook Signing Secrets

**Context:** Outbound webhooks to merchant integrations are signed with HMAC-SHA256. The signing secret is per-merchant and stored in the `merchant_webhook_configs` table.

**Storage:** PostgreSQL `merchant_webhook_configs` table, `SARDIS_SECRET_KEY` environment variable for platform-level HMAC.

**Procedure:**

1. **Generate new signing secret:**
   ```python
   import secrets
   new_secret = secrets.token_hex(32)
   ```
2. **Update merchant webhook configuration:**
   ```
   PUT /api/v2/admin/merchants/{merchant_id}/webhook-config
   {
     "signing_secret": "<new_secret>"
   }
   ```
3. **Notify merchant** of the new signing secret through their dashboard or secure channel
4. **Grace period:** Both old and new secrets are validated for 24 hours (dual-secret validation window)
5. **After grace period:** Old secret is automatically purged
6. **For platform-level `SARDIS_SECRET_KEY`:**
   ```bash
   gcloud run services update sardis-api-staging \
     --update-env-vars "SARDIS_SECRET_KEY=<new_secret_key_32chars_min>"
   ```

**Rollback:** Restore old signing secret in the database. Platform-level key rollback requires redeployment with old `SARDIS_SECRET_KEY`.

### 4.5 Stripe API Keys

**Context:** Stripe Issuing is used for virtual card management. Keys are used server-side only.

**Storage:** Stripe dashboard (primary), Cloud Run environment variable `STRIPE_SECRET_KEY`, GitHub Actions secret.

**Procedure:**

1. **Generate new key** in Stripe dashboard:
   - Navigate to Developers > API Keys
   - Roll the secret key (Stripe supports rolling with a grace period)
2. **Update environment:**
   ```bash
   gcloud run services update sardis-api-staging \
     --update-env-vars "STRIPE_SECRET_KEY=sk_live_<new_key>"
   ```
3. **Verify:**
   ```bash
   curl -f https://api-staging.sardis.sh/health
   ```
   Confirm `stripe` component reports `"status": "healthy"`.
4. **Expire old key** in Stripe dashboard after confirming all operations succeed
5. **Update GitHub Actions secrets** if used in CI

**Rollback:** Stripe allows re-enabling the old key within 72 hours of rolling. Update environment variables to revert.

### 4.6 JWT Signing Keys

**Context:** JWT tokens are used for dashboard and admin authentication. The signing key is used for HMAC-SHA256 or RS256 token signatures.

**Storage:** Environment variable `SARDIS_JWT_SECRET` or `SARDIS_JWT_PRIVATE_KEY`.

**Procedure:**

1. **Generate new signing key:**
   ```python
   import secrets
   new_jwt_secret = secrets.token_hex(64)
   ```
2. **Deploy with dual-key validation:**
   ```bash
   gcloud run services update sardis-api-staging \
     --update-env-vars "SARDIS_JWT_SECRET=<new_secret>,SARDIS_JWT_SECRET_PREVIOUS=<old_secret>"
   ```
   The auth middleware (`packages/sardis-api/src/sardis_api/routers/auth.py`) validates tokens against both the current and previous key during the grace period.
3. **Grace period:** 24 hours — tokens signed with the old key remain valid
4. **After grace period:** Remove the previous key:
   ```bash
   gcloud run services update sardis-api-staging \
     --update-env-vars "SARDIS_JWT_SECRET_PREVIOUS="
   ```
5. **Force session refresh** for admin users if rotating due to compromise

**Rollback:** Swap `SARDIS_JWT_SECRET` and `SARDIS_JWT_SECRET_PREVIOUS` values and redeploy.

### 4.7 Agent Signing Keys (Ed25519 / ECDSA-P256)

**Context:** Agent identity keys used for TAP (Trust Anchor Protocol) attestation. Managed by the key rotation system in `packages/sardis-core/src/sardis_v2_core/key_rotation.py`.

**Storage:** PostgreSQL `agent_keys` table (public keys only). Private keys are held by the agent operator.

**Procedure:**

1. **Initiate rotation** via API:
   ```
   POST /api/v2/agents/{agent_id}/keys/rotate
   {
     "new_public_key": "<hex_encoded_public_key>",
     "algorithm": "ed25519",
     "grace_period_hours": 24
   }
   ```
2. **System behavior:**
   - New key is created with `KeyStatus.ACTIVE`
   - Old key transitions to `KeyStatus.ROTATING` with a 24-hour grace period
   - Both keys are accepted for signature verification during the grace period
   - A `RotationEvent` is recorded in the audit log
3. **After grace period:** Old key automatically transitions to `KeyStatus.REVOKED`
4. **Verify:** Test agent can sign and submit a payment with the new key

**Rollback:** During the grace period, the old key is still valid. If the new key is compromised, explicitly revoke it:
```
POST /api/v2/agents/{agent_id}/keys/{new_key_id}/revoke
```

### 4.8 Redis Credentials (Upstash)

**Context:** Redis is used for rate limiting, caching, kill switch state, and session data.

**Storage:** Upstash console (primary), Cloud Run environment variable `SARDIS_REDIS_URL` / `UPSTASH_REDIS_URL`.

**Procedure:**

1. **Generate new credentials** in Upstash console:
   - Navigate to the database details
   - Reset the password or create a new database with the same configuration
2. **Update environment:**
   ```bash
   gcloud run services update sardis-api-staging \
     --update-env-vars "SARDIS_REDIS_URL=rediss://default:<new_pass>@<host>:6379,UPSTASH_REDIS_URL=rediss://default:<new_pass>@<host>:6379"
   ```
3. **Verify:**
   ```bash
   curl -f https://api-staging.sardis.sh/health
   ```
   Confirm `cache` component reports `"status": "healthy"`.
4. **Note:** Redis data is ephemeral (session data, rate limits). Loss of cached data during rotation is acceptable — it will be rebuilt automatically.

**Rollback:** Restore old credentials in Upstash and redeploy.

## 5. Emergency Rotation (Compromise Response)

When a secret is known or suspected to be compromised:

1. **Immediately** rotate the compromised secret using the relevant procedure above — skip grace periods
2. **Activate emergency freeze** if the compromise could affect payments:
   ```
   POST /api/v2/admin/emergency/freeze-all
   {
     "reason": "credential_compromise",
     "notes": "Rotating <secret_type> — suspected compromise"
   }
   ```
3. **Revoke all sessions** if JWT or API keys are compromised
4. **Audit:** Review access logs for the compromised credential:
   - Check API request logs for unauthorized usage
   - Review audit log for unexpected admin actions
5. **Notify:** Follow the Incident Response Plan (`docs/compliance/soc2/incident-response-plan.md`)
6. **Post-incident:** Document timeline, impact, and prevention measures

## 6. Verification Checklist (Post-Rotation)

After every rotation, verify:

- [ ] Health check endpoint returns all components healthy (`GET /health`)
- [ ] API authentication works with new credentials
- [ ] Webhook delivery succeeds with new signing secret (check delivery logs)
- [ ] No elevated error rates in monitoring (Cloud Run metrics)
- [ ] Audit log contains the rotation event
- [ ] Old credentials are revoked / expired
- [ ] GitHub Actions secrets are updated (if applicable)
- [ ] Documentation updated with rotation date

## 7. Secrets Inventory

All secrets are tracked in a secrets inventory with the following metadata:

| Field | Description |
|-------|-------------|
| Secret Name | Human-readable identifier |
| Storage Locations | All places the secret is stored/referenced |
| Last Rotated | Date of most recent rotation |
| Next Rotation Due | Based on rotation schedule |
| Owner | Team/person responsible |
| Rotation Procedure | Link to relevant section of this runbook |

The inventory is maintained as a restricted-access spreadsheet reviewed monthly by the Security team.

## 8. Automation

The following rotations are automated or semi-automated:

- **Agent signing keys:** Automatic grace period expiry via `key_rotation.py`
- **Session data:** Automatic TTL-based expiry in Redis (24 hours)
- **Gitleaks CI:** Automated secret scanning on every push and PR (`.github/workflows/secret-scan.yml`)
- **API key hashing:** Automatic SHA-256 hashing at creation — plaintext never stored

Future automation targets:

- Scheduled Neon credential rotation via API
- Stripe key rolling via Stripe API
- Automated health check verification after rotation

---

**Appendix A: Related Documents**

- Incident Response Plan (`docs/compliance/soc2/incident-response-plan.md`)
- Access Control Policy (`docs/compliance/soc2/access-control-policy.md`)
- Change Management Policy (`docs/compliance/soc2/change-management-policy.md`)
- Data Retention Policy (`docs/compliance/soc2/data-retention-policy.md`)
