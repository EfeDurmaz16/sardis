# TDD Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all TDD-flagged security, correctness, and architecture issues across 3 phases to move from 7.5→8.5 moat score and Medium→High execution confidence.

**Architecture:** Phase 1 fixes isolated bugs (no structural changes). Phase 2 unifies all payment execution through PaymentOrchestrator via a PreExecutionPipeline. Phase 3 replaces in-memory state with Redis/Postgres-backed durable stores and productizes evidence.

**Tech Stack:** Python 3.12, FastAPI, asyncpg, Redis, Pydantic, pytest, Foundry

**Atomic commits required.** Each task = 1 PR. Each step = 1 commit where noted.

---

## Phase 1: Security + Correctness (Days 1-30)

### Task 1: S1 — OAuth CSRF State Parameter

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/auth.py`
- Test: `packages/sardis-api/tests/test_auth_oauth_csrf.py`

**Step 1: Write the failing test**

```python
# packages/sardis-api/tests/test_auth_oauth_csrf.py
"""Tests for OAuth CSRF state parameter verification."""
import secrets
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from sardis_api.main import create_app
    app = create_app()
    return TestClient(app)


def test_oauth_callback_rejects_missing_state(client):
    """Callback must reject requests without state parameter."""
    resp = client.get("/api/v2/auth/google/callback", params={"code": "fake-code"})
    assert resp.status_code == 400
    assert "state" in resp.json().get("detail", "").lower()


def test_oauth_callback_rejects_invalid_state(client):
    """Callback must reject requests with non-matching state."""
    resp = client.get(
        "/api/v2/auth/google/callback",
        params={"code": "fake-code", "state": "wrong-state"},
    )
    assert resp.status_code == 400
    assert "state" in resp.json().get("detail", "").lower()


def test_oauth_initiation_returns_state(client):
    """OAuth initiation endpoint must include state in redirect URL."""
    resp = client.get("/api/v2/auth/google/login", allow_redirects=False)
    assert resp.status_code in (302, 307)
    location = resp.headers.get("location", "")
    assert "state=" in location
```

**Step 2: Run test to verify it fails**

Run: `cd packages/sardis-api && uv run pytest tests/test_auth_oauth_csrf.py -v`
Expected: FAIL — callback currently accepts requests without state.

**Step 3: Implement OAuth state verification**

In `auth.py`, find the OAuth initiation endpoint (the one that redirects to Google). Add:

```python
import secrets
from fastapi import Response

# In the OAuth initiation endpoint:
state_token = secrets.token_urlsafe(32)
# Store in a signed cookie (httponly, secure, samesite=lax, 10 min max-age)
response = RedirectResponse(url=f"{google_auth_url}&state={state_token}")
response.set_cookie(
    "oauth_state",
    state_token,
    httponly=True,
    secure=True,
    samesite="lax",
    max_age=600,
)
return response
```

In `google_oauth_callback` (line ~690), add at the top of the function:

```python
state_param = request.query_params.get("state")
state_cookie = request.cookies.get("oauth_state")
if not state_param or not state_cookie or not hmac.compare_digest(state_param, state_cookie):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or missing OAuth state parameter",
    )
# Clear the state cookie
response = Response()  # will be set later
# ... existing callback logic ...
```

**Step 4: Run test to verify it passes**

Run: `cd packages/sardis-api && uv run pytest tests/test_auth_oauth_csrf.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/sardis-api/src/sardis_api/routers/auth.py packages/sardis-api/tests/test_auth_oauth_csrf.py
git commit -m "fix(auth): add OAuth CSRF state parameter verification

Prevents CSRF attacks on Google OAuth callback by requiring a
cryptographic state token that matches between initiation and callback."
```

---

### Task 2: S2 — Remove Admin Login Fail-Open

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/auth.py:243`
- Test: `packages/sardis-api/tests/test_auth_admin_failopen.py`

**Step 1: Write the failing test**

```python
# packages/sardis-api/tests/test_auth_admin_failopen.py
"""Tests that admin login does not silently fall through on auth errors."""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from sardis_api.main import create_app
    app = create_app()
    return TestClient(app)


def test_admin_login_rejects_on_primary_auth_failure(client):
    """If primary auth raises, must return 401 — not fall through to legacy."""
    with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "sandbox"}):
        resp = client.post(
            "/api/v2/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        assert resp.status_code == 401


def test_admin_login_no_default_password_in_non_dev(client):
    """Default admin password must not work outside dev environment."""
    with patch.dict(os.environ, {
        "SARDIS_ENVIRONMENT": "sandbox",
        "SARDIS_ALLOW_INSECURE_DEFAULT_ADMIN_PASSWORD": "true",
    }):
        resp = client.post(
            "/api/v2/auth/login",
            json={"username": "admin", "password": "change-me-immediately"},
        )
        assert resp.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `cd packages/sardis-api && uv run pytest tests/test_auth_admin_failopen.py -v`
Expected: FAIL — currently falls through to legacy auth.

**Step 3: Remove the bare except and enforce explicit auth**

In `auth.py` around line 243, replace:

```python
# OLD — silent fallback
except Exception:
    pass  # Fall through to legacy auth
```

With:

```python
# NEW — fail explicitly, log the reason
except Exception as exc:
    logger.warning("Primary auth failed for user=%s: %s", request_data.get("username"), exc)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="authentication_failed",
    )
```

Then in the legacy admin password section (~line 254), add environment guard:

```python
env = os.getenv("SARDIS_ENVIRONMENT", "dev")
if env != "dev":
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="authentication_failed",
    )
# Only dev reaches here with default password
```

**Step 4: Run test to verify it passes**

Run: `cd packages/sardis-api && uv run pytest tests/test_auth_admin_failopen.py -v`
Expected: PASS

**Step 5: Run full auth test suite**

Run: `cd packages/sardis-api && uv run pytest tests/ -k auth -v`
Expected: All existing auth tests still pass.

**Step 6: Commit**

```bash
git add packages/sardis-api/src/sardis_api/routers/auth.py packages/sardis-api/tests/test_auth_admin_failopen.py
git commit -m "fix(auth): remove admin login silent fail-open fallback

Primary auth failure now returns 401 with logged reason instead of
silently falling through to legacy shared password. Default admin
password restricted to dev environment only."
```

---

### Task 3: S3 — Webhook Signatures Fail-Closed

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/treasury.py:449`
- Modify: `packages/sardis-api/src/sardis_api/routers/cpn.py:164`
- Test: `packages/sardis-api/tests/test_webhook_signature_enforcement.py`

**Step 1: Write the failing test**

```python
# packages/sardis-api/tests/test_webhook_signature_enforcement.py
"""Tests that webhook endpoints require signatures in non-dev environments."""
import os
from unittest.mock import patch

import pytest


def test_treasury_webhook_rejects_without_secret_in_sandbox():
    """Treasury webhook must reject in sandbox when secret not configured."""
    with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "sandbox"}, clear=False):
        # Import after env patch to pick up env
        from sardis_api.routers.treasury import _require_webhook_secret
        with pytest.raises(Exception) as exc_info:
            _require_webhook_secret(secret=None, env="sandbox")
        assert "webhook_secret" in str(exc_info.value).lower() or exc_info.value.status_code == 500


def test_treasury_webhook_allows_missing_secret_in_dev():
    """Treasury webhook may skip verification in dev."""
    from sardis_api.routers.treasury import _require_webhook_secret
    # Should not raise
    _require_webhook_secret(secret=None, env="dev")


def test_cpn_webhook_rejects_without_secret_in_sandbox():
    """CPN webhook must reject in sandbox when secret not configured."""
    from sardis_api.routers.cpn import _require_webhook_secret
    with pytest.raises(Exception) as exc_info:
        _require_webhook_secret(secret=None, env="sandbox")
    assert "webhook_secret" in str(exc_info.value).lower() or exc_info.value.status_code == 500
```

**Step 2: Run test to verify it fails**

Run: `cd packages/sardis-api && uv run pytest tests/test_webhook_signature_enforcement.py -v`
Expected: FAIL — functions don't exist yet or don't enforce in sandbox.

**Step 3: Add enforcement helper to both files**

In both `treasury.py` and `cpn.py`, add a helper:

```python
def _require_webhook_secret(secret: str | None, env: str) -> None:
    """Fail-closed: require webhook secret in all non-dev environments."""
    if not secret and env not in ("dev", "development", "local"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured — refusing to process unsigned webhook",
        )
```

Then replace the existing environment checks:

```python
# OLD (treasury.py ~line 456):
# if not secret and env in {"prod", "production"}:

# NEW:
_require_webhook_secret(secret, env)
```

Same pattern in `cpn.py`.

**Step 4: Run test to verify it passes**

Run: `cd packages/sardis-api && uv run pytest tests/test_webhook_signature_enforcement.py -v`
Expected: PASS

**Step 5: Run full webhook test suite**

Run: `cd packages/sardis-api && uv run pytest tests/ -k webhook -v`
Expected: All existing tests still pass.

**Step 6: Commit**

```bash
git add packages/sardis-api/src/sardis_api/routers/treasury.py packages/sardis-api/src/sardis_api/routers/cpn.py packages/sardis-api/tests/test_webhook_signature_enforcement.py
git commit -m "fix(webhooks): require signatures in all non-dev environments

Webhook endpoints now fail-closed when secret is not configured,
except in dev/local. Previously only enforced in production."
```

---

### Task 4: S4 — Secret Scanning CI + Gitignore Audit

**Files:**
- Create: `.gitleaks.toml`
- Create: `.github/workflows/secret-scan.yml`
- Verify: `.gitignore` (already covers .env files)

**Step 1: Create gitleaks config**

```toml
# .gitleaks.toml
title = "Sardis Secret Scanning"

[allowlist]
  description = "Global allowlist"
  paths = [
    '''\.lock$''',
    '''node_modules''',
    '''\.git''',
    '''contracts/lib''',
  ]

# Sardis-specific: flag any sk_, pk_, or API key patterns
[[rules]]
  id = "sardis-api-key"
  description = "Sardis API Key"
  regex = '''sk_(?:live|test|sandbox)_[A-Za-z0-9]{32,}'''
  tags = ["sardis", "api-key"]

[[rules]]
  id = "turnkey-private-key"
  description = "Turnkey MPC Private Key"
  regex = '''<PEM_PRIVATE_KEY_HEADER_PATTERN>'''  # See gitleaks docs for PEM regex
  tags = ["mpc", "private-key"]
```

**Step 2: Create secret scanning workflow**

```yaml
# .github/workflows/secret-scan.yml
name: Secret Scanning

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  gitleaks:
    name: Scan for secrets
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Step 3: Verify .gitignore coverage**

The .gitignore already contains:
- Line 39: `.env.local`
- Line 143: `.env.staging.*`
- Line 177: `deploy/gcp/staging/*.local.yaml`
- Line 181: `.env*.local`

This already covers all flagged files. No changes needed.

**Step 4: Commit**

```bash
git add .gitleaks.toml .github/workflows/secret-scan.yml
git commit -m "ci: add gitleaks secret scanning workflow

Scans all pushes and PRs for leaked secrets, API keys, and
private keys. Custom rules for Sardis API keys and Turnkey MPC keys."
```

**Step 5: Create credential rotation checklist (documentation only)**

Add to the PR description:
```
## Manual Action Required: Credential Rotation

The following credentials were found in tracked/local env files and must be rotated:

- [ ] OPENAI_API_KEY (sk_proj-...)
- [ ] SARDIS_SECRET_KEY
- [ ] JWT_SECRET_KEY
- [ ] SARDIS_ADMIN_PASSWORD
- [ ] DATABASE_URL (Neon PostgreSQL password)
- [ ] SARDIS_REDIS_URL (Upstash Redis password)
- [ ] LITHIC_API_KEY
- [ ] TURNKEY_API_KEY + TURNKEY_API_PRIVATE_KEY
- [ ] GROQ_API_KEY
- [ ] VERCEL_OIDC_TOKEN
- [ ] BETTER_AUTH_SECRET

After rotation, store new values in Google Secret Manager and inject via Cloud Run env vars.
```

---

### Task 5: C1 — Group-Policy TTL Fix

**Files:**
- Modify: `packages/sardis-core/src/sardis_v2_core/group_policy.py:238`
- Test: `packages/sardis-core/tests/test_group_policy_ttl.py`

**Step 1: Write the failing test**

```python
# packages/sardis-core/tests/test_group_policy_ttl.py
"""Tests for group policy per-period TTL correctness."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_monthly_counter_uses_monthly_ttl():
    """Monthly spend counter must use ~31-day TTL, not 24h."""
    from sardis_v2_core.group_policy import InMemoryGroupSpendingTracker

    mock_store = AsyncMock()
    mock_store.get = AsyncMock(return_value=None)
    tracker = InMemoryGroupSpendingTracker(store=mock_store)

    await tracker.record_spend("group-1", amount=100.0, period="monthly")

    # Find the set call and check TTL
    set_calls = mock_store.set.call_args_list
    assert len(set_calls) >= 1
    for call in set_calls:
        key = call.args[0] if call.args else call.kwargs.get("key", "")
        ttl = call.kwargs.get("ttl") or (call.args[2] if len(call.args) > 2 else None)
        if "monthly" in str(key):
            assert ttl >= 2_592_000, f"Monthly TTL must be >= 30 days, got {ttl}"


@pytest.mark.asyncio
async def test_daily_counter_uses_daily_ttl():
    """Daily spend counter must use 24h TTL."""
    from sardis_v2_core.group_policy import InMemoryGroupSpendingTracker

    mock_store = AsyncMock()
    mock_store.get = AsyncMock(return_value=None)
    tracker = InMemoryGroupSpendingTracker(store=mock_store)

    await tracker.record_spend("group-1", amount=100.0, period="daily")

    set_calls = mock_store.set.call_args_list
    for call in set_calls:
        key = call.args[0] if call.args else call.kwargs.get("key", "")
        ttl = call.kwargs.get("ttl") or (call.args[2] if len(call.args) > 2 else None)
        if "daily" in str(key):
            assert ttl == 86400, f"Daily TTL must be 86400, got {ttl}"
```

**Step 2: Run test to verify it fails**

Run: `cd packages/sardis-core && uv run pytest tests/test_group_policy_ttl.py -v`
Expected: FAIL — currently uses uniform 86400 TTL for all periods.

**Step 3: Split counters into per-period keys with correct TTLs**

In `group_policy.py`, replace the single `_store.set()` call (~line 238):

```python
# OLD:
# await self._store.set(group_id, {
#     "daily": str(daily),
#     "monthly": str(monthly),
#     "total": str(total),
# }, ttl=86400)

# NEW — per-period keys with correct TTLs:
_TTL_DAILY = 86_400       # 24 hours
_TTL_MONTHLY = 2_678_400  # 31 days
_TTL_TOTAL = 0            # no expiry

await self._store.set(f"{group_id}:daily", str(daily), ttl=_TTL_DAILY)
await self._store.set(f"{group_id}:monthly", str(monthly), ttl=_TTL_MONTHLY)
await self._store.set(f"{group_id}:total", str(total), ttl=_TTL_TOTAL)
```

Update the corresponding `get` logic to read from per-period keys:

```python
# OLD:
# data = await self._store.get(group_id)
# daily = float(data.get("daily", 0)) if data else 0.0

# NEW:
daily = float(await self._store.get(f"{group_id}:daily") or 0)
monthly = float(await self._store.get(f"{group_id}:monthly") or 0)
total = float(await self._store.get(f"{group_id}:total") or 0)
```

**Step 4: Run test to verify it passes**

Run: `cd packages/sardis-core && uv run pytest tests/test_group_policy_ttl.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/sardis-core/src/sardis_v2_core/group_policy.py packages/sardis-core/tests/test_group_policy_ttl.py
git commit -m "fix(group-policy): use period-appropriate TTLs for spend counters

Daily counter: 24h TTL. Monthly counter: 31-day TTL. Total: no expiry.
Previously all counters used 24h TTL, causing monthly budgets to reset
daily and allowing 30x overspend."
```

---

### Task 6: C2 — Group-Budget Decrement After Payment

**Files:**
- Modify: `packages/sardis-core/src/sardis_v2_core/orchestrator.py:736`
- Modify: `packages/sardis-api/src/sardis_api/dependencies.py` (DI wiring)
- Test: `packages/sardis-core/tests/test_orchestrator_group_spend.py`

**Step 1: Write the failing test**

```python
# packages/sardis-core/tests/test_orchestrator_group_spend.py
"""Tests that orchestrator records group spend after successful payment."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_orchestrator_records_group_spend_on_success():
    """After successful chain execution, group_policy.record_spend must be called."""
    from sardis_v2_core.orchestrator import PaymentOrchestrator

    mock_group_policy = AsyncMock()
    mock_group_policy.record_spend = AsyncMock()

    orchestrator = PaymentOrchestrator(
        wallet_manager=AsyncMock(async_validate_policies=AsyncMock(return_value=MagicMock(allowed=True))),
        compliance=AsyncMock(preflight=AsyncMock(return_value=MagicMock(allowed=True))),
        chain_executor=AsyncMock(dispatch_payment=AsyncMock(return_value=MagicMock(tx_hash="0x123"))),
        ledger=MagicMock(append=MagicMock()),
        group_policy=mock_group_policy,
    )

    # Execute a payment
    mandate = MagicMock(
        mandate_id="test-mandate-1",
        subject="agent-1",
        amount_minor=1000,
        group_id="group-1",
    )
    await orchestrator.execute(mandate)

    # Verify group spend was recorded
    mock_group_policy.record_spend.assert_called_once()
    call_args = mock_group_policy.record_spend.call_args
    assert call_args.kwargs.get("group_id") == "group-1" or call_args.args[0] == "group-1"
```

**Step 2: Run test to verify it fails**

Run: `cd packages/sardis-core && uv run pytest tests/test_orchestrator_group_spend.py -v`
Expected: FAIL — orchestrator doesn't accept or call group_policy.

**Step 3: Add group_policy to orchestrator constructor and call record_spend**

In `orchestrator.py`, update `PaymentOrchestrator.__init__` (~line 429):

```python
def __init__(
    self,
    wallet_manager,
    compliance,
    chain_executor,
    ledger,
    group_policy=None,  # NEW
    reconciliation_queue=None,
):
    # ... existing init ...
    self._group_policy = group_policy  # NEW
```

After the existing `async_record_spend` call (~line 736):

```python
# Existing:
if hasattr(self._wallet_manager, "async_record_spend"):
    await self._wallet_manager.async_record_spend(payment)

# NEW — record group spend
if self._group_policy and hasattr(payment, "group_id") and payment.group_id:
    try:
        await self._group_policy.record_spend(
            group_id=payment.group_id,
            amount=payment.amount_minor,
        )
    except Exception as e:
        logger.error("Failed to record group spend for group=%s: %s", payment.group_id, e)
```

In `dependencies.py`, update the orchestrator property (~line 160):

```python
@cached_property
def payment_orchestrator(self) -> Any:
    from sardis_v2_core.orchestrator import PaymentOrchestrator
    return PaymentOrchestrator(
        wallet_manager=self.wallet_manager,
        compliance=self.compliance_engine,
        chain_executor=self.chain_executor,
        ledger=self.ledger_store,
        group_policy=self.group_policy,  # NEW
    )
```

**Step 4: Run test to verify it passes**

Run: `cd packages/sardis-core && uv run pytest tests/test_orchestrator_group_spend.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/sardis-core/src/sardis_v2_core/orchestrator.py packages/sardis-api/src/sardis_api/dependencies.py packages/sardis-core/tests/test_orchestrator_group_spend.py
git commit -m "fix(orchestrator): record group spend after successful payment

Group budgets were checked pre-execution but never decremented
post-execution, allowing unlimited overspend against group limits."
```

---

### Task 7: C3 — Queue Interface Mismatch Fix

**Files:**
- Modify: `packages/sardis-core/src/sardis_v2_core/orchestrator.py:759`

**Step 1: Fix the method name**

In `orchestrator.py` at line 759, change:

```python
# OLD:
self._reconciliation_queue.append(spend_recon)

# NEW:
self._reconciliation_queue.enqueue(spend_recon)
```

**Step 2: Run existing tests**

Run: `cd packages/sardis-core && uv run pytest tests/ -k orchestrat -v`
Expected: PASS (existing tests use InMemoryReconciliationQueue which has both methods, but this ensures protocol compliance).

**Step 3: Commit**

```bash
git add packages/sardis-core/src/sardis_v2_core/orchestrator.py
git commit -m "fix(orchestrator): use enqueue() matching ReconciliationQueuePort protocol

Changed .append() to .enqueue() at line 759 to match the
ReconciliationQueuePort protocol definition. Prevents AttributeError
when a protocol-conformant persistent queue is plugged in."
```

---

### Task 8: C4 — AGIT Fail-Close

**Files:**
- Modify: `packages/sardis-core/src/sardis_v2_core/control_plane.py:186`
- Modify: `packages/sardis-core/src/sardis_v2_core/config.py`
- Test: `packages/sardis-core/tests/test_agit_fail_close.py`

**Step 1: Write the failing test**

```python
# packages/sardis-core/tests/test_agit_fail_close.py
"""Tests that AGIT verification errors reject payments by default."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_agit_error_rejects_payment_by_default():
    """When AGIT verification raises, payment must be rejected (fail-closed)."""
    from sardis_v2_core.control_plane import ControlPlane

    mock_agit = AsyncMock()
    mock_agit.verify_policy_chain = AsyncMock(side_effect=RuntimeError("AGIT service unavailable"))

    settings = MagicMock()
    settings.agit_fail_open = False

    cp = ControlPlane(settings=settings, agit_policy_engine=mock_agit)
    intent = MagicMock(intent_id="test-intent-1")

    result = await cp.execute(intent)

    assert result.status == "rejected"
    assert "agit" in result.reason.lower()


@pytest.mark.asyncio
async def test_agit_error_allows_when_fail_open_enabled():
    """When SARDIS_AGIT_FAIL_OPEN=true, AGIT errors are non-blocking."""
    from sardis_v2_core.control_plane import ControlPlane

    mock_agit = AsyncMock()
    mock_agit.verify_policy_chain = AsyncMock(side_effect=RuntimeError("AGIT unavailable"))

    settings = MagicMock()
    settings.agit_fail_open = True

    cp = ControlPlane(settings=settings, agit_policy_engine=mock_agit)
    intent = MagicMock(intent_id="test-intent-2")

    result = await cp.execute(intent)
    # Should not be rejected — continues execution
    assert result.status != "rejected" or "agit" not in getattr(result, "reason", "").lower()
```

**Step 2: Run test to verify it fails**

Run: `cd packages/sardis-core && uv run pytest tests/test_agit_fail_close.py -v`
Expected: FAIL — currently logs warning and continues.

**Step 3: Add config field**

In `config.py`, add to `SardisSettings` (after `erc4337_rollout_stage`):

```python
# AGIT policy chain enforcement
agit_fail_open: bool = False  # Default: fail-closed (safe)
```

With env var: `SARDIS_AGIT_FAIL_OPEN=false`

**Step 4: Fix the except handler in control_plane.py**

At line 186-190, replace:

```python
# OLD:
except Exception as e:
    logger.warning(
        "ControlPlane: AGIT chain check failed for intent=%s: %s (non-blocking)",
        intent.intent_id, e,
    )

# NEW:
except Exception as e:
    if self._settings.agit_fail_open:
        logger.warning(
            "ControlPlane: AGIT chain check failed for intent=%s: %s (fail-open enabled, continuing)",
            intent.intent_id, e,
        )
    else:
        logger.error(
            "ControlPlane: AGIT chain check failed for intent=%s: %s (fail-closed, rejecting)",
            intent.intent_id, e,
        )
        return ExecutionResult(
            status="rejected",
            reason=f"AGIT policy verification unavailable: {e}",
            intent_id=intent.intent_id,
        )
```

**Step 5: Run test to verify it passes**

Run: `cd packages/sardis-core && uv run pytest tests/test_agit_fail_close.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add packages/sardis-core/src/sardis_v2_core/control_plane.py packages/sardis-core/src/sardis_v2_core/config.py packages/sardis-core/tests/test_agit_fail_close.py
git commit -m "fix(control-plane): AGIT verification errors now reject payments

Default behavior changed from non-blocking warning to fail-closed
rejection. Override with SARDIS_AGIT_FAIL_OPEN=true for incident
management. Prevents payments from bypassing policy integrity checks
when AGIT service is unavailable."
```

---

## Phase 2: Single Execution Path (Days 31-60)

### Task 9: A1 — Create PreExecutionPipeline

**Files:**
- Create: `packages/sardis-core/src/sardis_v2_core/pre_execution_pipeline.py`
- Test: `packages/sardis-core/tests/test_pre_execution_pipeline.py`

**Step 1: Write the failing test**

```python
# packages/sardis-core/tests/test_pre_execution_pipeline.py
"""Tests for PreExecutionPipeline composability."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_pipeline_runs_all_hooks_in_order():
    """Pipeline executes hooks in order and returns first rejection."""
    from sardis_v2_core.pre_execution_pipeline import PreExecutionPipeline, HookResult

    call_order = []

    async def hook_a(intent):
        call_order.append("a")
        return HookResult(decision="approve")

    async def hook_b(intent):
        call_order.append("b")
        return HookResult(decision="approve")

    pipeline = PreExecutionPipeline(hooks=[hook_a, hook_b])
    result = await pipeline.evaluate(MagicMock())

    assert result.decision == "approve"
    assert call_order == ["a", "b"]


@pytest.mark.asyncio
async def test_pipeline_stops_on_first_rejection():
    """Pipeline short-circuits on first reject."""
    from sardis_v2_core.pre_execution_pipeline import PreExecutionPipeline, HookResult

    async def hook_approve(intent):
        return HookResult(decision="approve")

    async def hook_reject(intent):
        return HookResult(decision="reject", reason="trust_score_too_low")

    async def hook_never_reached(intent):
        raise AssertionError("Should not be reached")

    pipeline = PreExecutionPipeline(hooks=[hook_approve, hook_reject, hook_never_reached])
    result = await pipeline.evaluate(MagicMock())

    assert result.decision == "reject"
    assert result.reason == "trust_score_too_low"


@pytest.mark.asyncio
async def test_pipeline_skip_does_not_block():
    """Skip results are ignored, pipeline continues."""
    from sardis_v2_core.pre_execution_pipeline import PreExecutionPipeline, HookResult

    async def hook_skip(intent):
        return HookResult(decision="skip")

    async def hook_approve(intent):
        return HookResult(decision="approve")

    pipeline = PreExecutionPipeline(hooks=[hook_skip, hook_approve])
    result = await pipeline.evaluate(MagicMock())
    assert result.decision == "approve"
```

**Step 2: Run test to verify it fails**

Run: `cd packages/sardis-core && uv run pytest tests/test_pre_execution_pipeline.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Implement PreExecutionPipeline**

```python
# packages/sardis-core/src/sardis_v2_core/pre_execution_pipeline.py
"""Pre-execution pipeline for composable payment authorization hooks."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Literal

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HookResult:
    """Result of a single pre-execution hook."""
    decision: Literal["approve", "reject", "skip"]
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


# Hook type: async callable that takes an intent and returns HookResult
PreExecutionHook = Callable[[Any], Coroutine[Any, Any, HookResult]]


class PreExecutionPipeline:
    """Composable pipeline of pre-execution authorization hooks.

    Hooks run in order. First 'reject' short-circuits.
    'skip' results are ignored. All 'approve' = approved.
    """

    def __init__(self, hooks: list[PreExecutionHook] | None = None):
        self._hooks = hooks or []

    def add_hook(self, hook: PreExecutionHook) -> None:
        self._hooks.append(hook)

    async def evaluate(self, intent: Any) -> HookResult:
        for hook in self._hooks:
            try:
                result = await hook(intent)
            except Exception as e:
                logger.error("Pre-execution hook %s failed: %s", hook.__name__, e)
                return HookResult(decision="reject", reason=f"Hook error: {e}")

            if result.decision == "reject":
                logger.info("Pre-execution rejected by %s: %s", hook.__name__, result.reason)
                return result
            elif result.decision == "skip":
                continue

        return HookResult(decision="approve")
```

**Step 4: Run test to verify it passes**

Run: `cd packages/sardis-core && uv run pytest tests/test_pre_execution_pipeline.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/sardis-core/src/sardis_v2_core/pre_execution_pipeline.py packages/sardis-core/tests/test_pre_execution_pipeline.py
git commit -m "feat(core): add PreExecutionPipeline for composable authorization hooks

Ordered pipeline of async hooks (AGIT, KYA, FIDES, trust scoring).
First rejection short-circuits. Hook errors fail-closed.
Foundation for Phase 2 single execution path unification."
```

---

### Task 10: A1b — Extract Control Plane Steps Into Pipeline Hooks

**Files:**
- Modify: `packages/sardis-core/src/sardis_v2_core/control_plane.py`
- Create: `packages/sardis-core/src/sardis_v2_core/hooks/agit_hook.py`
- Create: `packages/sardis-core/src/sardis_v2_core/hooks/kya_hook.py`
- Create: `packages/sardis-core/src/sardis_v2_core/hooks/fides_hook.py`
- Test: `packages/sardis-core/tests/test_pipeline_hooks.py`

Extract each verification step from `control_plane.py` into a standalone async hook function that returns `HookResult`. Each hook is a simple adapter:

```python
# packages/sardis-core/src/sardis_v2_core/hooks/agit_hook.py
"""AGIT policy chain verification hook for PreExecutionPipeline."""
from __future__ import annotations
import logging
from ..pre_execution_pipeline import HookResult

logger = logging.getLogger(__name__)


def create_agit_hook(agit_engine, fail_open: bool = False):
    """Factory that returns a pipeline-compatible AGIT hook."""
    async def agit_hook(intent) -> HookResult:
        try:
            verification = await agit_engine.verify_policy_chain(intent)
            if not verification.valid:
                return HookResult(
                    decision="reject",
                    reason=f"AGIT policy chain invalid: {verification.reason}",
                    evidence={"broken_at": getattr(verification, "broken_at", None)},
                )
            return HookResult(decision="approve", evidence={"agit": "valid"})
        except Exception as e:
            if fail_open:
                logger.warning("AGIT hook failed (fail-open): %s", e)
                return HookResult(decision="skip")
            return HookResult(decision="reject", reason=f"AGIT unavailable: {e}")

    agit_hook.__name__ = "agit_hook"
    return agit_hook
```

Same pattern for KYA and FIDES hooks. Then deprecate ControlPlane:

```python
# In control_plane.py, add at top of class:
import warnings

class ControlPlane:
    """DEPRECATED: Use PaymentOrchestrator with PreExecutionPipeline instead."""

    async def execute(self, intent):
        warnings.warn(
            "ControlPlane.execute() is deprecated. Use PaymentOrchestrator.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Delegate to orchestrator if available, else run legacy path
        ...
```

Write tests for each hook. Commit per hook.

---

### Task 11: A2 — Migrate wallets.py to Orchestrator

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/wallets.py:767-817`
- Test: `packages/sardis-api/tests/test_wallets_orchestrator.py`

Replace the inline policy → compliance → chain execution block with:

```python
# OLD (lines 767-817): ~50 lines of inline policy check, compliance, chain execution

# NEW:
from sardis_v2_core.execution_intent import ExecutionIntent

intent = ExecutionIntent(
    mandate=mandate,
    source="wallet_transfer",
    wallet_id=wallet_id,
    fee_calc=fee_calc,
)
result = await deps.payment_orchestrator.execute(intent)
if result.status == "rejected":
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=result.reason,
    )
receipt = result.chain_receipt
```

Remove TODO comments. Write integration test verifying orchestrator is called.

---

### Task 12: A2b — Migrate mandates.py to Orchestrator

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/mandates.py:400-431`

Same pattern as Task 11. Replace lines 400-422 with `ExecutionIntent` + `orchestrator.execute()`.

---

### Task 13: A2c — Migrate ap2.py to Orchestrator

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/ap2.py:466-502`

Same pattern. The inline policy validation (lines 473-502) moves into the pre-execution pipeline hooks.

---

### Task 14: A3 — DI Lockdown

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/dependencies.py`

Remove `chain_executor` as a directly injectable dependency for routers. Keep it as an internal dependency of `payment_orchestrator`.

```python
# Remove or make private:
# @cached_property
# def chain_executor(self) -> Any:

# Replace with private method:
@cached_property
def _chain_executor(self) -> Any:
    """Internal — only used by PaymentOrchestrator."""
    from sardis_chain.executor import ChainExecutor
    return ChainExecutor(settings=self._settings)

@cached_property
def payment_orchestrator(self) -> Any:
    from sardis_v2_core.orchestrator import PaymentOrchestrator
    return PaymentOrchestrator(
        wallet_manager=self.wallet_manager,
        compliance=self.compliance_engine,
        chain_executor=self._chain_executor,  # private
        ledger=self.ledger_store,
        group_policy=self.group_policy,
        pre_execution_pipeline=self._build_pipeline(),
    )
```

Verify no router imports `deps.chain_executor` directly:

Run: `grep -r "deps.chain_executor" packages/sardis-api/src/sardis_api/routers/`
Expected: No results.

---

### Task 15: A4 — Unified PaymentResult

**Files:**
- Create: `packages/sardis-core/src/sardis_v2_core/payment_result.py`
- Modify: routers to serialize PaymentResult

```python
# packages/sardis-core/src/sardis_v2_core/payment_result.py
"""Unified payment execution result."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PaymentResult:
    """Standard result from PaymentOrchestrator.execute()."""
    status: str  # "success", "rejected", "failed"
    mandate_id: str = ""
    tx_hash: str = ""
    chain: str = ""
    reason: str = ""
    reason_codes: list[str] = field(default_factory=list)
    policy_evidence: dict[str, Any] = field(default_factory=dict)
    compliance_evidence: dict[str, Any] = field(default_factory=dict)
    chain_receipt: Any = None
    ledger_entry_id: str = ""
    attestation_id: str = ""
```

---

## Phase 3: Durable State + Moat Tightening (Days 61-90)

### Task 16: D1 — Redis-Backed Duplicate Suppression

**Files:**
- Create: `packages/sardis-core/src/sardis_v2_core/dedup_store.py`
- Modify: `packages/sardis-core/src/sardis_v2_core/orchestrator.py:440`
- Test: `packages/sardis-core/tests/test_dedup_store.py`

```python
# packages/sardis-core/src/sardis_v2_core/dedup_store.py
"""Durable deduplication store backed by Redis."""
from __future__ import annotations
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEDUP_TTL = 86_400  # 24 hours


class DurableDedupStore:
    """Redis-backed mandate deduplication. Fail-closed if Redis unavailable."""

    def __init__(self, redis_client):
        self._redis = redis_client

    async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
        """Return existing result if duplicate, else store and return None."""
        key = f"sardis:dedup:{mandate_id}"
        existing = await self._redis.get(key)
        if existing:
            return json.loads(existing)
        await self._redis.set(key, json.dumps(result, default=str), ex=_DEDUP_TTL)
        return None


class FailClosedDedupStore:
    """Rejects all payments when Redis is unavailable."""

    async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
        raise RuntimeError("Dedup store unavailable — payment rejected for safety")
```

Replace `self._executed_mandates` dict in orchestrator with `DurableDedupStore`.

---

### Task 17: D2 — Persistent Reconciliation Queue

**Files:**
- Create: `packages/sardis-core/src/sardis_v2_core/reconciliation_queue_postgres.py`
- Create: `packages/sardis-api/migrations/057_reconciliation_queue.sql`
- Test: `packages/sardis-core/tests/test_reconciliation_queue_postgres.py`

Migration:

```sql
-- packages/sardis-api/migrations/057_reconciliation_queue.sql
CREATE TABLE IF NOT EXISTS reconciliation_queue (
    id              BIGSERIAL PRIMARY KEY,
    entry_type      TEXT NOT NULL,
    payload_json    JSONB NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    CHECK (status IN ('pending', 'processing', 'resolved', 'failed'))
);

CREATE INDEX idx_recon_queue_status ON reconciliation_queue (status) WHERE status = 'pending';
```

Implement `PostgresReconciliationQueue` conforming to `ReconciliationQueuePort`.

Add to `validate_production_config`: reject `InMemoryReconciliationQueue` in prod/sandbox.

---

### Task 18: D3 + D4 — Durable Replay Cache + Rate Limiter Enforcement

**Files:**
- Create: `packages/sardis-protocol/src/sardis_protocol/replay_cache_redis.py`
- Modify: `packages/sardis-protocol/src/sardis_protocol/verifier.py:53`
- Modify: `packages/sardis-protocol/src/sardis_protocol/rate_limiter.py:489`
- Modify: `packages/sardis-core/src/sardis_v2_core/config.py` (production validation)
- Test: `packages/sardis-protocol/tests/test_replay_cache_redis.py`

```python
# packages/sardis-protocol/src/sardis_protocol/replay_cache_redis.py
"""Redis-backed replay cache for mandate deduplication."""
from __future__ import annotations
import time


class RedisReplayCache:
    """Redis-backed replay cache. Fail-closed."""

    def __init__(self, redis_client, ttl_seconds: int = 86_400):
        self._redis = redis_client
        self._ttl = ttl_seconds

    async def seen(self, mandate_hash: str) -> bool:
        key = f"sardis:replay:{mandate_hash}"
        existing = await self._redis.get(key)
        if existing:
            return True
        await self._redis.set(key, str(int(time.time())), ex=self._ttl)
        return False
```

In `rate_limiter.py:489`, add:

```python
def get_rate_limiter(config=None, redis_url=None):
    global _rate_limiter
    if _rate_limiter is None:
        if redis_url:
            _rate_limiter = RedisAgentRateLimiter(config, redis_url)
        else:
            import os
            env = os.getenv("SARDIS_ENVIRONMENT", "dev")
            if env not in ("dev", "development", "local"):
                raise RuntimeError(
                    "Redis URL required for rate limiting in non-dev environments. "
                    "Set SARDIS_REDIS_URL or REDIS_URL."
                )
            _rate_limiter = AgentRateLimiter(config)
    return _rate_limiter
```

---

### Task 19: E1 + E2 — Policy Attestation Envelope + Verifier Report

**Files:**
- Create: `packages/sardis-core/src/sardis_v2_core/attestation_envelope.py`
- Create: `packages/sardis-api/src/sardis_api/routers/attestation.py`
- Modify: `packages/sardis-core/src/sardis_v2_core/orchestrator.py` (emit attestation)
- Test: `packages/sardis-api/tests/test_attestation_endpoint.py`

New endpoint `GET /api/v2/payments/{payment_id}/attestation` returns:

```json
{
  "attestation_id": "att_...",
  "timestamp": "2026-03-15T12:00:00Z",
  "agent_did": "did:sardis:agent-123",
  "policy_rules_applied": ["daily_limit", "merchant_allowlist"],
  "evidence_chain": ["policy_hash:abc123", "compliance:pass", "chain:0x456"],
  "ap2_mandate_ref": "mandate_abc",
  "verification_report": {
    "mandate_chain_valid": true,
    "policy_compliance": "pass",
    "kya_score": 0.85,
    "provenance": "turnkey_mpc"
  },
  "signature": "ed25519:..."
}
```

---

### Task 20: E3 + E4 — README Accuracy + Deployment Manifest + GH Description + Landing Page

**Files:**
- Modify: `README.md`
- Modify: `contracts/deployments/base.json`
- Modify: `contracts/deployments/base_sepolia.json`
- Modify: `landing/` (if needed)

README rewrite — add maturity tiers:

```markdown
## Protocol & Feature Maturity

| Feature | Status | Description |
|---------|--------|-------------|
| Spending Policy Engine | **Production** | Deterministic NL policy, atomic spend tracking |
| AP2 Mandate Verification | **Production** | Full mandate chain verification |
| USDC Payments (Base) | **Production** | Non-custodial MPC wallet execution |
| Hosted Checkout | **Pilot** | Merchant checkout flows with session security |
| ERC-8183 Agentic Jobs | **Pilot** | On-chain job escrow (conservative caps) |
| x402 Protocol | **Pilot** | HTTP-native micropayments |
| Multi-chain (Polygon, Arbitrum) | **Experimental** | Chain routing implemented, not production-tested |
| UCP MCP Transport | **Experimental** | Partial implementation |
```

Update GH repo description to match. Check landing page for claims that need updating.

---

## Commit & PR Strategy

Each task = 1 atomic PR with:
- Descriptive commit message (conventional commits)
- Tests included in same PR
- No unrelated changes

Branch naming: `fix/s1-oauth-csrf`, `fix/c1-group-policy-ttl`, `feat/a1-pre-execution-pipeline`, etc.
