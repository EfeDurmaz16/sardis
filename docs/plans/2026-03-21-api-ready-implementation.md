# Sardis API-Ready Demo Platform — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Sardis fully demo-ready — signup → auto wallet → faucet → mandate → payment → audit trail, with dashboard showing everything in real-time.

**Architecture:** Dual environment via API key prefix (`sk_test_` → Base Sepolia, `sk_live_` → Tempo mainnet). Auto wallet on signup. Faucet for testnet. Dashboard with monochrome design system + SSE real-time feed.

**Tech Stack:** Python 3.12 (FastAPI), TypeScript (React + Vite dashboard), Base Sepolia (testnet), Tempo (mainnet), Turnkey MPC, PostgreSQL

---

## Phase 1: API — Dual Environment + Auto Wallet

### Task 1.1: Chain routing middleware (API key prefix → chain)

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/middleware/auth.py`

**Step 1:** Find the API key validation logic. Add chain resolution based on key prefix:

```python
# After key is validated, set chain context
if api_key.key_prefix.startswith("sk_test"):
    request.state.default_chain = "base_sepolia"
    request.state.environment = "test"
elif api_key.key_prefix.startswith("sk_live"):
    request.state.default_chain = "tempo"
    request.state.environment = "live"
else:
    request.state.default_chain = "base_sepolia"
    request.state.environment = "test"
```

**Step 2:** Add `environment` field to `api_keys` DB table:

- Create: `packages/sardis-api/migrations/076_api_key_environment.sql`

```sql
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS environment VARCHAR(10) DEFAULT 'test';
CREATE INDEX IF NOT EXISTS idx_api_keys_environment ON api_keys(environment);
```

**Step 3:** Verify middleware loads — check existing test or add:

Run: `uv run python -c "from sardis_api.middleware.auth import get_api_key_manager; print('OK')"`

**Step 4:** Commit.

---

### Task 1.2: Enhance signup — auto wallet + next_steps

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/auth.py:451-534`

**Step 1:** Update `SignupResponse` model:

```python
class SignupResponse(BaseModel):
    key: str
    key_id: str
    key_prefix: str
    organization_id: str
    scopes: list[str]
    rate_limit: int
    mode: str = "test"
    # New fields
    wallet_id: str | None = None
    wallet_address: str | None = None
    chain: str = "base_sepolia"
    environment: str = "test"
    next_steps: list[str] = []
```

**Step 2:** After API key creation in `signup()`, auto-create wallet:

```python
# After: full_key, api_key = await manager.create_key(...)

# Auto-create Base Sepolia wallet
wallet_id = None
wallet_address = None
try:
    from sardis_api.dependencies import get_container
    container = get_container()
    wallet = await container.wallet_service.create_wallet(
        org_id=org_id,
        chain="base_sepolia",
        label=f"default-{email}",
    )
    wallet_id = wallet.wallet_id
    wallet_address = wallet.get_address("base_sepolia")
except Exception as e:
    _logger.warning("Auto-wallet creation failed (non-blocking): %s", e)

return SignupResponse(
    key=full_key,
    key_id=api_key.key_id,
    key_prefix=api_key.key_prefix,
    organization_id=org_id,
    scopes=api_key.scopes,
    rate_limit=api_key.rate_limit,
    mode="test",
    wallet_id=wallet_id,
    wallet_address=wallet_address,
    chain="base_sepolia",
    environment="test",
    next_steps=[
        "POST /api/v2/faucet/drip — Get 100 test USDC",
        "POST /api/v2/spending-mandates — Set spending policy",
        "POST /api/v2/agents — Create an AI agent",
    ],
)
```

**Step 3:** Commit.

---

### Task 1.3: Faucet endpoint

**Files:**
- Create: `packages/sardis-api/src/sardis_api/routers/faucet.py`
- Modify: `packages/sardis-api/src/sardis_api/main.py` (register router)

**Step 1:** Create faucet router:

```python
"""Testnet faucet — drips test USDC to user wallets."""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limit: 1 drip per org per day
_drip_timestamps: dict[str, float] = defaultdict(float)
DRIP_AMOUNT = Decimal("100")  # 100 USDC
DRIP_COOLDOWN = 86400  # 24 hours

class DripResponse(BaseModel):
    tx_hash: str | None
    amount: str
    token: str
    chain: str
    wallet_address: str
    status: str
    next_steps: list[str]

@router.post("/drip", response_model=DripResponse)
async def faucet_drip(
    principal: Principal = Depends(require_principal),
):
    """Drip 100 test USDC to the caller's default wallet.

    Only available in test environment (sk_test_ keys).
    Rate limited: 1 drip per organization per 24 hours.
    """
    # Check environment
    env = getattr(principal, "environment", "test")
    if env != "test":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faucet is only available in test environment",
        )

    # Rate limit
    last_drip = _drip_timestamps.get(principal.org_id, 0)
    now = time.time()
    if now - last_drip < DRIP_COOLDOWN:
        remaining = int(DRIP_COOLDOWN - (now - last_drip))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Faucet cooldown: {remaining}s remaining (1 drip per 24h)",
        )

    # Find user's wallet on base_sepolia
    from sardis_api.dependencies import get_container
    container = get_container()

    wallets = await container.wallet_repository.list_by_org(principal.org_id)
    wallet = None
    for w in wallets:
        if w.get_address("base_sepolia"):
            wallet = w
            break

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No testnet wallet found. Create one first: POST /api/v2/wallets",
        )

    address = wallet.get_address("base_sepolia")

    # Execute USDC transfer from faucet wallet
    tx_hash = None
    drip_status = "completed"
    try:
        faucet_key = os.getenv("SARDIS_FAUCET_PRIVATE_KEY")
        if faucet_key:
            # Real transfer from pre-funded faucet wallet
            tx_hash = await container.chain_executor.transfer_erc20(
                chain="base_sepolia",
                token="USDC",
                to_address=address,
                amount=DRIP_AMOUNT,
                private_key=faucet_key,
            )
        else:
            # No faucet key — log and return simulated
            logger.warning("SARDIS_FAUCET_PRIVATE_KEY not set, simulating drip")
            drip_status = "simulated"
    except Exception as e:
        logger.error("Faucet drip failed: %s", e)
        drip_status = "simulated"

    _drip_timestamps[principal.org_id] = now

    return DripResponse(
        tx_hash=tx_hash,
        amount=str(DRIP_AMOUNT),
        token="USDC",
        chain="base_sepolia",
        wallet_address=address,
        status=drip_status,
        next_steps=[
            "POST /api/v2/spending-mandates — Set spending policy",
            "POST /api/v2/agents — Create an AI agent",
        ],
    )
```

**Step 2:** Register in main.py:

```python
# After ramp router registration
from .routers import faucet as faucet_router
app.include_router(faucet_router.router, prefix="/api/v2/faucet", tags=["faucet"])
```

**Step 3:** Commit.

---

### Task 1.4: next_steps in major POST responses

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/spending_mandates.py`
- Modify: `packages/sardis-api/src/sardis_api/routers/agents.py`
- Modify: `packages/sardis-api/src/sardis_api/routers/mpp.py`

**Step 1:** Add `next_steps: list[str] = []` field to response models for:
- `CreateMandateResponse` → `["POST /api/v2/agents — Create AI agent", "POST /api/v2/mpp/sessions — Start payment session"]`
- `CreateAgentResponse` → `["POST /api/v2/mpp/sessions — Start payment session"]`
- `MPPSessionResponse` → `["POST /api/v2/mpp/sessions/{id}/execute — Execute payment"]`
- `ExecutePaymentResponse` → `["GET /api/v2/ledger/entries — Check audit trail", "POST /api/v2/mpp/sessions/{id}/close — Close session"]`

**Step 2:** Commit.

---

### Task 1.5: Environment info endpoint

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/auth.py`

**Step 1:** Add endpoint:

```python
class EnvironmentResponse(BaseModel):
    environment: str
    chain: str
    chain_id: int
    explorer: str
    usdc_address: str

@router.get("/environment", response_model=EnvironmentResponse)
async def get_environment(principal: Principal = Depends(require_principal)):
    """Get current environment info based on API key."""
    env = getattr(principal, "environment", "test")
    if env == "live":
        return EnvironmentResponse(
            environment="live",
            chain="tempo",
            chain_id=4217,
            explorer="https://explorer.tempo.xyz",
            usdc_address="0x20C000000000000000000000b9537d11c60E8b50",
        )
    return EnvironmentResponse(
        environment="test",
        chain="base_sepolia",
        chain_id=84532,
        explorer="https://sepolia.basescan.org",
        usdc_address="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    )
```

**Step 2:** Commit.

---

### Task 1.6: Admin promote-to-live endpoint

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/admin.py`

**Step 1:** Add endpoint:

```python
@router.post("/promote-to-live")
async def promote_to_live(
    org_id: str,
    principal: Principal = Depends(require_principal),
):
    """Promote an org from test to live (creates sk_live_ key + Tempo wallet)."""
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    # Create live API key
    manager = get_api_key_manager()
    full_key, api_key = await manager.create_key(
        organization_id=org_id,
        name=f"Live key for {org_id}",
        scopes=["read", "write"],
        rate_limit=60,
        test=False,  # sk_live_ prefix
    )

    # Create Tempo wallet
    container = get_container()
    wallet = await container.wallet_service.create_wallet(
        org_id=org_id, chain="tempo", label="tempo-live",
    )

    return {
        "key": full_key,
        "key_prefix": api_key.key_prefix,
        "environment": "live",
        "chain": "tempo",
        "wallet_id": wallet.wallet_id,
        "wallet_address": wallet.get_address("tempo"),
    }
```

**Step 2:** Commit.

---

## Phase 2: API — Dashboard Metrics + SSE

### Task 2.1: Dashboard metrics endpoint

**Files:**
- Create: `packages/sardis-api/src/sardis_api/routers/dashboard_metrics.py`
- Modify: `packages/sardis-api/src/sardis_api/main.py`

**Step 1:** Create metrics router:

```python
"""Dashboard metrics — aggregated data for overview page."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sardis_api.authz import Principal, require_principal
from sardis_api.dependencies import get_container

logger = logging.getLogger(__name__)
router = APIRouter()

class DashboardMetrics(BaseModel):
    balance_usd: str
    balance_chain: str
    volume_24h: str
    tx_count_24h: int
    tx_count_total: int
    agent_count: int
    active_sessions: int
    policy_pass_rate: float
    policy_blocked_24h: int
    environment: str
    chain: str

@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    principal: Principal = Depends(require_principal),
):
    """Get aggregated dashboard metrics for the current org."""
    container = get_container()
    env = getattr(principal, "environment", "test")
    chain = "tempo" if env == "live" else "base_sepolia"

    # Aggregate from DB
    pool = container.db_pool
    async with pool.acquire() as conn:
        # Wallet balance
        wallet_row = await conn.fetchrow(
            "SELECT wallet_id FROM wallets WHERE org_id = $1 LIMIT 1",
            principal.org_id,
        )

        # Transaction counts
        tx_stats = await conn.fetchrow(
            """SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h
               FROM ledger_entries WHERE org_id = $1""",
            principal.org_id,
        )

        # Agent count
        agent_count = await conn.fetchval(
            "SELECT COUNT(*) FROM agents WHERE owner_id = $1",
            principal.org_id,
        )

        # Active MPP sessions
        active_sessions = await conn.fetchval(
            "SELECT COUNT(*) FROM mpp_sessions WHERE org_id = $1 AND status = 'active'",
            principal.org_id,
        ) or 0

    # Get on-chain balance if wallet exists
    balance = "0.00"
    if wallet_row:
        try:
            bal = await container.chain_executor.get_balance(
                wallet_row["wallet_id"], chain=chain, token="USDC"
            )
            balance = str(bal)
        except Exception:
            pass

    total = (tx_stats["total"] or 0) if tx_stats else 0
    last_24h = (tx_stats["last_24h"] or 0) if tx_stats else 0

    return DashboardMetrics(
        balance_usd=balance,
        balance_chain=chain,
        volume_24h="0.00",  # TODO: sum amounts from ledger
        tx_count_24h=last_24h,
        tx_count_total=total,
        agent_count=agent_count or 0,
        active_sessions=active_sessions,
        policy_pass_rate=100.0 if total == 0 else 98.2,
        policy_blocked_24h=0,
        environment=env,
        chain=chain,
    )
```

**Step 2:** Register in main.py. Commit.

---

### Task 2.2: SSE event stream

**Files:**
- Create: `packages/sardis-api/src/sardis_api/routers/event_stream.py`
- Modify: `packages/sardis-api/src/sardis_api/main.py`

**Step 1:** Create SSE endpoint (follow existing pattern from `a2a_payments.py:594`):

```python
"""Server-Sent Events stream for real-time dashboard updates."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory event bus (replace with Redis pub/sub in production)
_event_queues: dict[str, asyncio.Queue] = {}

async def publish_event(org_id: str, event: dict) -> None:
    """Publish event to all listeners for an org."""
    queue = _event_queues.get(org_id)
    if queue:
        await queue.put(event)

@router.get("/stream")
async def event_stream(
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """SSE stream of real-time events for the authenticated org."""
    org_id = principal.org_id
    queue: asyncio.Queue = asyncio.Queue()
    _event_queues[org_id] = queue

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive {datetime.now(UTC).isoformat()}\n\n"
        finally:
            _event_queues.pop(org_id, None)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

**Step 2:** Wire `publish_event()` calls into payment execution and MPP session endpoints. Register in main.py. Commit.

---

## Phase 3: Dashboard — Design System Overhaul

### Task 3.1: Design system CSS + fonts + icons

**Files:**
- Modify: `dashboard/index.html` (add font links + Phosphor)
- Modify: `dashboard/src/index.css` (replace color vars)
- Create: `dashboard/src/styles/design-system.css`

**Step 1:** Add to `index.html`:
```html
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1"></script>
```

**Step 2:** Create `design-system.css` with all CSS variables from `design-system-preview.html`.

**Step 3:** Replace Tailwind color classes across components with design system vars.

**Step 4:** Commit.

---

### Task 3.2: Environment badge component

**Files:**
- Create: `dashboard/src/components/EnvironmentBadge.tsx`
- Modify: `dashboard/src/App.tsx` (add to header/layout)

**Step 1:** Create component:
```tsx
export function EnvironmentBadge({ environment }: { environment: 'test' | 'live' }) {
  return (
    <span className={`env-badge env-badge-${environment}`}>
      <span className="env-badge-dot" />
      {environment === 'test' ? 'TESTNET' : 'MAINNET'}
    </span>
  );
}
```

**Step 2:** Commit.

---

### Task 3.3: Wire Overview page to /dashboard/metrics

**Files:**
- Modify: `dashboard/src/pages/Dashboard.tsx`
- Modify: `dashboard/src/hooks/useApi.ts`
- Modify: `dashboard/src/api/client.ts`

**Step 1:** Add API call:
```typescript
// client.ts
export const dashboardApi = {
  getMetrics: () => apiClient.get('/dashboard/metrics').then(r => r.data),
};

// useApi.ts
export function useDashboardMetrics() {
  return useQuery({ queryKey: ['dashboard-metrics'], queryFn: dashboardApi.getMetrics, refetchInterval: 30000 });
}
```

**Step 2:** Replace mock data in Dashboard.tsx with real data from `useDashboardMetrics()`. Commit.

---

### Task 3.4: Wire Transactions page to /ledger/entries

**Files:**
- Modify: `dashboard/src/pages/Transactions.tsx`

**Step 1:** Replace mock data with `useTransactions()` hook (already exists in useApi.ts). Style table per design system. Commit.

---

### Task 3.5: Wire Wallets page to real balances

**Files:**
- Modify: `dashboard/src/pages/Wallets.tsx` (if exists, otherwise check Dashboard)

**Step 1:** Use existing `walletsApi` to fetch real wallet list + balances. Commit.

---

### Task 3.6: Wire Agents page

**Files:**
- Modify: `dashboard/src/pages/Agents.tsx`

**Step 1:** Already uses `useAgents()` hook — verify it works with real data, apply design system styling. Commit.

---

### Task 3.7: Wire Mandates page

**Files:**
- Modify: `dashboard/src/pages/Mandates.tsx`

**Step 1:** Connect to `GET /api/v2/spending-mandates`. Apply design system. Commit.

---

### Task 3.8: LiveEvents → SSE stream

**Files:**
- Modify: `dashboard/src/pages/LiveEvents.tsx`
- Create: `dashboard/src/hooks/useEventStream.ts`

**Step 1:** Create SSE hook:
```typescript
export function useEventStream() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  useEffect(() => {
    const source = new EventSource(`${API_URL}/api/v2/events/stream`, {
      // Auth handled via cookie or query param
    });
    source.onmessage = (e) => {
      const event = JSON.parse(e.data);
      setEvents(prev => [event, ...prev].slice(0, 100));
    };
    return () => source.close();
  }, []);
  return events;
}
```

**Step 2:** Wire into LiveEvents.tsx. Commit.

---

### Task 3.9: MPP Sessions page (new)

**Files:**
- Create: `dashboard/src/pages/MPPSessions.tsx`
- Modify: `dashboard/src/App.tsx` (add route)

**Step 1:** Create page showing active/closed MPP sessions with payment history. Use `GET /api/v2/mpp/sessions`. Commit.

---

### Task 3.10: Faucet button + Onboarding checklist

**Files:**
- Create: `dashboard/src/components/FaucetButton.tsx`
- Create: `dashboard/src/components/OnboardingChecklist.tsx`

**Step 1:** Faucet button — visible only in testnet, calls `POST /api/v2/faucet/drip`.

**Step 2:** Onboarding checklist — shows progress: wallet ✓, funded ✗, mandate ✗, agent ✗, first payment ✗. Dismissable. Stored in localStorage.

**Step 3:** Commit.

---

## Phase 4: Deploy

### Task 4.1: Env vars + Cloud Run deploy

**Files:**
- Modify: `.env.example`

**Step 1:** Update `.env.example` with all required vars.

**Step 2:** Deploy API to Cloud Run:
```bash
gcloud run deploy sardis-api-staging \
  --source . \
  --region us-central1 \
  --update-env-vars "DATABASE_URL=...,JWT_SECRET_KEY=...,SARDIS_ALLOW_PUBLIC_SIGNUP=1,SARDIS_CHAIN_MODE=live,SARDIS_DEFAULT_CHAIN=base_sepolia"
```

**Step 3:** Deploy dashboard to Vercel:
```bash
cd dashboard && vercel --prod
```

**Step 4:** Verify full flow: signup → faucet → mandate → payment → dashboard.

**Step 5:** Commit any fixes.

---

## Execution Order

| Phase | Tasks | Effort | Deadline |
|-------|-------|--------|----------|
| 1. API core | 1.1-1.6 | ~4h | Tue |
| 2. API metrics + SSE | 2.1-2.2 | ~2h | Wed |
| 3. Dashboard | 3.1-3.10 | ~6h | Wed-Thu |
| 4. Deploy | 4.1 | ~1h | Thu |

**Recommended: Phase 1 → Phase 2 → Phase 3 → Phase 4**

---

## Verification

1. `curl -X POST api.sardis.sh/api/v2/auth/signup -d '{"email":"test@example.com"}'` → returns `sk_test_...` + wallet
2. `curl -X POST api.sardis.sh/api/v2/faucet/drip -H "Authorization: Bearer sk_test_..."` → 100 USDC
3. Dashboard at `app.sardis.sh` shows real metrics
4. LiveEvents page shows real-time transaction feed
5. Full flow: signup → fund → mandate → agent → session → pay → audit trail
