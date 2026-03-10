# Access Control Policy

**Document ID:** SARDIS-SOC2-ACP-001
**Version:** 1.0
**Effective Date:** 2026-03-10
**Last Reviewed:** 2026-03-10
**Owner:** Engineering / Security
**Classification:** Internal

---

## 1. Purpose

This policy defines the access control requirements for the Sardis platform, covering authentication, authorization, session management, and the principle of least privilege. It satisfies SOC 2 Trust Service Criteria CC6.1 (logical access security), CC6.2 (user authentication), CC6.3 (credential management), and CC6.4 (access restriction).

## 2. Scope

This policy applies to all access to Sardis systems, including:

- Sardis API endpoints
- Administrative functions and dashboards
- Database access (Neon PostgreSQL)
- Infrastructure services (Cloud Run, Vercel, Upstash)
- MPC wallet operations (Turnkey)
- Third-party service integrations (Stripe, iDenfy, Elliptic, Alchemy)
- Source code repository (GitHub)

## 3. Authentication Model

Sardis supports two authentication mechanisms, as defined in `packages/sardis-api/src/sardis_api/authz.py`:

### 3.1 API Key Authentication

**Use case:** Server-to-server integrations, agent-to-platform communication.

| Attribute | Detail |
|-----------|--------|
| **Format** | `sk_live_<random>` (production) or `sk_test_<random>` (sandbox) |
| **Storage** | SHA-256 hash stored in PostgreSQL `api_keys` table |
| **Plaintext exposure** | Shown to the user exactly once at creation; never stored or logged |
| **Transport** | `Authorization: Bearer sk_...` header or `X-API-Key` header |
| **Validation** | SHA-256 hash of submitted key compared against database record |
| **Scoping** | Each key carries a list of scopes (e.g., `["payments", "wallets"]`) |
| **Revocation** | Immediate — delete the hash from the database |

**Implementation:** `packages/sardis-api/src/sardis_api/middleware/auth.py` (`get_api_key` dependency).

### 3.2 JWT Token Authentication

**Use case:** Dashboard and admin UI sessions.

| Attribute | Detail |
|-----------|--------|
| **Issuance** | Issued upon successful login via `packages/sardis-api/src/sardis_api/routers/auth.py` |
| **Algorithm** | HMAC-SHA256 (symmetric) or RS256 (asymmetric) |
| **Expiry** | Short-lived tokens (configurable, default 1 hour) |
| **Refresh** | Refresh token mechanism for session continuity |
| **Signing key** | `SARDIS_JWT_SECRET` environment variable |
| **Validation** | Signature verification + expiry check on every request |
| **Revocation** | Token invalidation via Redis blacklist on logout |

**Implementation:** `packages/sardis-api/src/sardis_api/routers/auth.py` (`get_current_user` dependency).

### 3.3 Unified Principal Model

Both authentication mechanisms resolve to a `Principal` dataclass (`packages/sardis-api/src/sardis_api/authz.py`):

```python
@dataclass(frozen=True)
class Principal:
    kind: Literal["api_key", "jwt"]
    organization_id: str
    scopes: list[str]
    user: UserInfo | None = None
    api_key: APIKey | None = None
```

Key properties:

- `is_admin` — Returns `True` if the principal has "admin" or "*" scope (API key) or "admin" role (JWT)
- `org_id` — Organization context for multi-tenant isolation
- `user_id` — Actor identifier for audit logging (username for JWT, key_id for API key)

The `require_principal` dependency is applied to all protected endpoints and enforces that at least one valid authentication mechanism is present.

## 4. Authorization Model

### 4.1 Role-Based Access Control (RBAC)

| Role | Scope | Capabilities |
|------|-------|-------------|
| **Standard** | `["payments", "wallets"]` | Create/manage wallets, execute payments, view transactions |
| **Read-Only** | `["read"]` | View wallets, transactions, and account status |
| **Cards** | `["cards"]` | Virtual card operations (create, fund, freeze) |
| **Admin** | `["admin"]` or `["*"]` | All operations including emergency controls, user management, configuration |

### 4.2 Endpoint-Level Authorization

All API endpoints enforce authorization through FastAPI dependencies:

| Endpoint Category | Auth Required | Admin Required | Additional Controls |
|-------------------|---------------|----------------|---------------------|
| Health checks (`/health`, `/ready`, `/live`) | No | No | Public endpoints for monitoring |
| Checkout public (`/sessions/client/...`) | No | No | Client secret authentication |
| Standard API (`/api/v2/wallets`, `/api/v2/payments`) | Yes (`require_principal`) | No | Scope-based access |
| Admin endpoints (`/api/v2/admin/...`) | Yes | Yes (`Principal.is_admin`) | Rate-limited (10 req/min) |
| Emergency endpoints (`/api/v2/admin/emergency/...`) | Yes | Yes | MFA required, rate-limited (5 req/min), audit-logged |

### 4.3 Multi-Tenant Isolation

Every data query is scoped to the authenticated principal's `organization_id`:

- Wallet queries filter by `org_id`
- Transaction queries filter by `org_id`
- Agent queries filter by `org_id`
- API key management is scoped to `org_id`

Cross-organization access is not possible through the API, even for admin principals (admin functions operate within their own organization context unless explicitly querying system-wide data).

## 5. MPC Key Access Control (Turnkey)

### 5.1 Non-Custodial Architecture

Sardis implements a non-custodial model for wallet management:

| Principle | Implementation |
|-----------|----------------|
| **No private key storage** | Sardis never stores, logs, or transmits private keys |
| **MPC key shares** | Distributed across Turnkey's infrastructure; no single party holds the complete key |
| **Signing authorization** | Sardis requests transaction signing via Turnkey API; Turnkey enforces its own authorization |
| **Wallet ownership** | Wallets are Smart Accounts (Safe v1.4.1) owned by the organization |

### 5.2 Turnkey Access Controls

| Access Type | Requirement |
|-------------|-------------|
| **API authentication** | Turnkey API key pair (`TURNKEY_API_KEY`, `TURNKEY_API_PUBLIC_KEY`) |
| **Organization isolation** | `TURNKEY_ORGANIZATION_ID` scopes all operations to the Sardis organization |
| **Sub-organization support** | Per-customer sub-organizations for additional isolation (if configured) |
| **Activity logs** | Turnkey provides audit logs of all signing operations |

### 5.3 Wallet Freeze Mechanism

Wallet operations can be halted at multiple levels:

1. **Individual wallet freeze:** `POST /api/v2/wallets/{wallet_id}/freeze` — sets `frozen = TRUE` on the wallet record
2. **Organization freeze:** Kill switch at org scope blocks all payments for the organization
3. **Global freeze:** Emergency freeze-all (`POST /api/v2/admin/emergency/freeze-all`) freezes all wallets and activates the global kill switch

When a wallet is frozen, the kill switch dependency (`require_kill_switch_clear`) blocks payment execution before any signing request reaches Turnkey.

## 6. Rate Limiting

### 6.1 Rate Limit Tiers

| Tier | Limit | Scope | Enforcement |
|------|-------|-------|-------------|
| **Standard API** | 100 requests/minute | Per API key or JWT session | Redis-backed sliding window counter |
| **Admin API** | 10 requests/minute | Per admin principal | Redis-backed; applied via `@admin_rate_limit()` |
| **Sensitive Admin** | 5 requests/minute | Per admin principal | Applied via `@admin_rate_limit(is_sensitive=True)` on emergency endpoints |
| **Checkout public** | 60 requests/minute | Per IP address | Rate limiting without authentication |

### 6.2 Rate Limit Enforcement

- **Production:** Redis-backed (Upstash) — distributed, accurate across all instances
- **Development:** In-memory fallback when Redis is unavailable
- **Required in production:** `SARDIS_REDIS_URL` must be set in non-dev environments for rate limiting to function (enforced by configuration validation)

### 6.3 Rate Limit Response

When a rate limit is exceeded, the API returns:

```
HTTP 429 Too Many Requests
{
  "detail": "Rate limit exceeded. Try again in X seconds."
}
```

Headers include `Retry-After` with the number of seconds until the limit resets.

## 7. Principle of Least Privilege

### 7.1 API Key Scoping

API keys are created with the minimum scopes necessary for the intended use case:

- Payment processing agents receive `["payments", "wallets"]` — not admin scopes
- Read-only monitoring integrations receive `["read"]`
- Admin keys (`["admin"]` or `["*"]`) are issued only to authorized personnel and tracked in the audit log

### 7.2 Internal Service Access

| Service | Access Model |
|---------|--------------|
| **Database** | Application connects via connection string; no direct database access for operators in production |
| **Chain executor** | Private in DI container — only accessible through `PaymentOrchestrator` (`packages/sardis-core/src/sardis_v2_core/orchestrator.py`) |
| **Kill switch** | Read access for all authenticated endpoints (dependency check); write access restricted to admin principals |
| **Turnkey** | API credentials scoped to the Sardis organization; no cross-organization access |

### 7.3 Infrastructure Access

| System | Access Control |
|--------|---------------|
| **GitHub repository** | Team-based permissions; branch protection on `main` |
| **Cloud Run** | Google IAM roles; limited to engineering team |
| **Neon console** | Team-based access; production database restricted to senior engineers |
| **Vercel dashboard** | Team-based access; production deploy restricted |
| **Upstash console** | Team-based access |
| **Turnkey dashboard** | Organization admin access; MFA required |
| **Stripe dashboard** | Role-based access; production restricted to authorized personnel |

## 8. Multi-Factor Authentication (MFA)

### 8.1 MFA Requirements

| Action | MFA Required |
|--------|-------------|
| Emergency freeze/unfreeze | Yes (via `require_mfa_if_enabled` dependency) |
| Admin API key creation | Yes |
| Admin configuration changes | Yes |
| Standard API operations | No (API key authentication is sufficient) |
| Dashboard login | Recommended; enforced for admin users |

### 8.2 MFA Implementation

MFA is enforced through the `require_mfa_if_enabled` FastAPI dependency applied to emergency and sensitive admin endpoints (`packages/sardis-api/src/sardis_api/middleware/mfa.py`).

The emergency router explicitly declares this dependency:

```python
router = APIRouter(
    prefix="/api/v2/admin/emergency",
    tags=["admin", "emergency"],
    dependencies=[Depends(require_mfa_if_enabled)],
)
```

## 9. Session Management

### 9.1 Session Lifecycle

| Phase | Implementation |
|-------|----------------|
| **Creation** | JWT issued upon authentication; session ID stored in Redis |
| **Validation** | JWT signature + expiry checked on every request |
| **Timeout** | 24-hour maximum session duration (Redis TTL) |
| **Inactivity timeout** | Configurable; default 1 hour for admin sessions |
| **Termination** | Explicit logout invalidates token in Redis; session data purged |

### 9.2 Session Security Controls

- Tokens are transmitted only over TLS (HTTPS)
- Session tokens are not logged (redacted in request logging middleware)
- Concurrent sessions are permitted but tracked
- Session data in Redis has a hard TTL (24 hours) — no indefinite sessions

## 10. Anonymous Access Restrictions

The `require_principal` dependency includes a safety mechanism for development environments:

```python
# From packages/sardis-api/src/sardis_api/authz.py
if allow_anon and env in {"dev", "test", "local"}:
    # Only allow anonymous access from loopback addresses
    client_ip = request.client.host
    loopback = {"127.0.0.1", "::1", "localhost", "testclient"}
    if client_ip not in loopback:
        raise HTTPException(status_code=401)
```

This ensures:

- Anonymous access is never permitted in production, staging, or sandbox environments
- Even in development, anonymous access is restricted to loopback addresses
- `SARDIS_ALLOW_ANON` must be explicitly set AND the environment must be `dev`/`test`/`local`

## 11. Access Reviews

### 11.1 Periodic Reviews

| Review Type | Frequency | Owner | Scope |
|-------------|-----------|-------|-------|
| API key audit | Quarterly | Security | All active API keys: scope appropriateness, last-used date, organization association |
| Admin access review | Quarterly | Engineering Lead | All principals with admin scope: necessity verification |
| Infrastructure access review | Semi-annually | CTO | Cloud Run, Neon, Vercel, Turnkey, Stripe access |
| GitHub permissions review | Semi-annually | Engineering Lead | Repository access, branch protection rules |

### 11.2 Access Revocation Triggers

Access is immediately revoked when:

- An employee leaves the organization
- A role change removes the need for access
- A security incident involves the credential
- An API key has not been used for 90 days (flagged for review)
- An access review identifies unnecessary permissions

## 12. Audit Trail

All access-related events are logged:

| Event | Log Location | Details Captured |
|-------|-------------|------------------|
| API key creation | Audit log | Key ID (not plaintext), scopes, organization, creator |
| API key revocation | Audit log | Key ID, revoker, reason |
| Authentication success | API request log | Principal kind, organization, endpoint |
| Authentication failure | API request log + security log | IP address, attempted auth method, failure reason |
| Admin action | Audit log (via `log_admin_action`) | Action type, actor, request details, timestamp |
| Emergency freeze/unfreeze | `emergency_freeze_events` table | Event ID, action, triggered_by, wallets_affected, reason, notes |
| Kill switch activation | Audit log | Scope, reason, activated_by |
| MFA challenge | Security log | Principal, success/failure, timestamp |

## 13. Compliance Mapping

| SOC 2 Criterion | Control | Section |
|-----------------|---------|---------|
| CC6.1 — Logical access security | API key + JWT authentication | Section 3 |
| CC6.2 — User authentication | Principal model, MFA | Sections 3, 8 |
| CC6.3 — Credential management | SHA-256 hashing, rotation, secret scanning | Sections 3.1, 11 |
| CC6.4 — Access restriction | RBAC, scoped keys, multi-tenant isolation | Sections 4, 7 |
| CC6.5 — Data disposal | Session TTL, key revocation | Section 9 |
| CC6.6 — Physical access (N/A) | Cloud-hosted — deferred to cloud provider SOC 2 reports | N/A |

## 14. Review Cadence

This policy is reviewed:

- **Annually** as part of the SOC 2 audit cycle
- **Upon material changes** to the authentication or authorization system
- **After any incident** involving unauthorized access

---

**Appendix A: Related Documents**

- Secrets Rotation Runbook (`docs/compliance/soc2/secrets-rotation-runbook.md`)
- Incident Response Plan (`docs/compliance/soc2/incident-response-plan.md`)
- Evidence Matrix (`docs/compliance/soc2/evidence-matrix.md`)
- Data Retention Policy (`docs/compliance/soc2/data-retention-policy.md`)

**Appendix B: Key Source Code References**

| Component | Path |
|-----------|------|
| Principal + require_principal | `packages/sardis-api/src/sardis_api/authz.py` |
| API key middleware | `packages/sardis-api/src/sardis_api/middleware/auth.py` |
| JWT authentication | `packages/sardis-api/src/sardis_api/routers/auth.py` |
| MFA middleware | `packages/sardis-api/src/sardis_api/middleware/mfa.py` |
| Emergency endpoints (MFA enforced) | `packages/sardis-api/src/sardis_api/routers/emergency.py` |
| Kill switch dependency | `packages/sardis-api/src/sardis_api/kill_switch_dep.py` |
| Admin rate limiting | `packages/sardis-api/src/sardis_api/routers/admin.py` |
| Audit logging | `packages/sardis-api/src/sardis_api/audit_log.py` |
| Key rotation | `packages/sardis-core/src/sardis_v2_core/key_rotation.py` |
| Wallet management | `packages/sardis-wallet/src/sardis_wallet/manager.py` |
| Spending policy (authorization) | `packages/sardis-core/src/sardis_v2_core/spending_policy.py` |
