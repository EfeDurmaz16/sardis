# Non-Custodial Architecture Migration Guide

**Version:** 1.0  
**Date:** January 11, 2026  
**Status:** Implementation Guide

---

## Overview

This guide documents the migration from a custodial to non-custodial architecture. The key principle: **Sardis never holds funds. Wallets are sign-only.**

---

## Core Principles

### Before (Custodial)

```python
# OLD: Wallet holds balance
@dataclass
class Wallet:
    wallet_id: str
    agent_id: str
    balance: Decimal  # ❌ We hold funds
    token_balances: dict[str, Decimal]  # ❌ We manage balances
    
    def transfer(self, amount: Decimal, to: str):
        if self.balance < amount:
            raise InsufficientBalance()
        self.balance -= amount  # ❌ We update balance
        # ... execute transaction
```

### After (Non-Custodial)

```python
# NEW: Wallet is sign-only
@dataclass
class Wallet:
    wallet_id: str
    agent_id: str
    mpc_provider: str  # "turnkey" | "fireblocks"
    addresses: dict[str, str]  # chain -> address mapping
    # NO balance storage ✅
    
    async def sign_transaction(
        self,
        tx: TransactionRequest,
    ) -> str:
        """Sign transaction via MPC. No balance check."""
        # Balance is on-chain, not in our database
        return await mpc_signer.sign(tx)
```

---

## Migration Checklist

### Phase 1: Wallet Model Refactoring

#### 1.1 Remove Balance Storage

**File:** `packages/sardis-core/src/sardis_v2_core/wallets.py`

**Before:**
```python
@dataclass
class Wallet:
    wallet_id: str
    agent_id: str
    balance: Decimal
    token_balances: dict[str, TokenBalance]
    spent_total: Decimal
```

**After:**
```python
@dataclass
class Wallet:
    wallet_id: str
    agent_id: str
    mpc_provider: str
    addresses: dict[str, str]  # chain -> address
    created_at: datetime
    # NO balance fields
```

**Action Items:**
- [ ] Remove `balance` field
- [ ] Remove `token_balances` field
- [ ] Remove `spent_total` field
- [ ] Add `addresses` dict (chain -> address mapping)
- [ ] Add `mpc_provider` field

#### 1.2 Update Wallet Operations

**File:** `packages/sardis-core/src/sardis_v2_core/wallets.py`

**Before:**
```python
def can_spend(self, amount: Decimal) -> bool:
    """Check if wallet has sufficient balance."""
    return self.balance >= amount

def transfer(self, amount: Decimal, to: str):
    """Transfer funds (custodial)."""
    if not self.can_spend(amount):
        raise InsufficientBalance()
    self.balance -= amount
    # ... execute
```

**After:**
```python
async def get_balance(self, chain: str, token: str) -> Decimal:
    """Get balance from on-chain (read-only)."""
    address = self.addresses.get(chain)
    if not address:
        raise ValueError(f"No address for chain {chain}")
    
    # Query blockchain for balance
    rpc = get_rpc_client(chain)
    balance = await rpc.get_token_balance(address, token)
    return Decimal(balance)

async def sign_transaction(
    self,
    chain: str,
    to: str,
    amount: Decimal,
    token: str,
) -> str:
    """Sign transaction via MPC (non-custodial)."""
    # No balance check here - that's policy engine's job
    # Just sign the transaction
    tx_request = TransactionRequest(
        chain=chain,
        to_address=to,
        amount=int(amount * 10**6),  # Convert to minor units
        token=token,
    )
    return await mpc_signer.sign(self.wallet_id, tx_request)
```

**Action Items:**
- [ ] Remove `can_spend()` method
- [ ] Remove `transfer()` method
- [ ] Add `get_balance()` method (read-only from chain)
- [ ] Add `sign_transaction()` method (sign-only)
- [ ] Update all callers

#### 1.3 Update Database Schema

**File:** `packages/sardis-core/src/sardis_v2_core/database.py`

**Before:**
```sql
CREATE TABLE wallets (
    wallet_id VARCHAR PRIMARY KEY,
    agent_id VARCHAR NOT NULL,
    balance NUMERIC(20,6) DEFAULT 0,
    token_balances JSONB,
    spent_total NUMERIC(20,6) DEFAULT 0,
    ...
);
```

**After:**
```sql
CREATE TABLE wallets (
    wallet_id VARCHAR PRIMARY KEY,
    agent_id VARCHAR NOT NULL,
    mpc_provider VARCHAR NOT NULL,  -- "turnkey" | "fireblocks"
    addresses JSONB,  -- {"base": "0x...", "polygon": "0x..."}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ...
    -- NO balance columns
);

-- Separate table for on-chain balance snapshots (optional, for analytics)
CREATE TABLE wallet_balance_snapshots (
    id UUID PRIMARY KEY,
    wallet_id VARCHAR REFERENCES wallets(wallet_id),
    chain VARCHAR NOT NULL,
    token VARCHAR NOT NULL,
    balance NUMERIC(20,6) NOT NULL,
    block_number BIGINT,
    snapshot_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(wallet_id, chain, token, block_number)
);
```

**Action Items:**
- [ ] Create migration script to remove balance columns
- [ ] Add `mpc_provider` column
- [ ] Add `addresses` JSONB column
- [ ] Create optional `wallet_balance_snapshots` table (for analytics)
- [ ] Update all queries

---

### Phase 2: Policy Engine Updates

#### 2.1 Balance Checks Move to Policy Engine

**File:** `packages/sardis-core/src/sardis_v2_core/spending_policy.py`

**Before:**
```python
def evaluate(
    self,
    wallet: Wallet,
    amount: Decimal,
    merchant_id: str,
) -> PolicyResult:
    # Check wallet balance
    if wallet.balance < amount:
        return PolicyResult(denied=True, reason="insufficient_balance")
    
    # Check policy limits
    if amount > self.limit_per_tx:
        return PolicyResult(denied=True, reason="exceeds_per_tx_limit")
    # ...
```

**After:**
```python
async def evaluate(
    self,
    wallet: Wallet,
    amount: Decimal,
    merchant_id: str,
    chain: str,
    token: str,
) -> PolicyResult:
    # Check on-chain balance (read-only)
    balance = await wallet.get_balance(chain, token)
    if balance < amount:
        return PolicyResult(denied=True, reason="insufficient_balance")
    
    # Check policy limits
    if amount > self.limit_per_tx:
        return PolicyResult(denied=True, reason="exceeds_per_tx_limit")
    
    # Check time-window limits
    spent_today = await self.get_spent_today(wallet.wallet_id)
    if spent_today + amount > self.daily_limit:
        return PolicyResult(denied=True, reason="exceeds_daily_limit")
    # ...
```

**Action Items:**
- [ ] Make `evaluate()` async
- [ ] Add `chain` and `token` parameters
- [ ] Use `wallet.get_balance()` instead of `wallet.balance`
- [ ] Update all callers

---

### Phase 3: API Endpoint Updates

#### 3.1 Remove Balance Endpoints (or Make Read-Only)

**File:** `packages/sardis-api/src/sardis_api/routers/wallets.py`

**Before:**
```python
@router.get("/wallets/{wallet_id}/balance")
async def get_wallet_balance(wallet_id: str):
    wallet = await wallet_repo.get(wallet_id)
    return {"balance": wallet.balance}  # ❌ From database
```

**After:**
```python
@router.get("/wallets/{wallet_id}/balance")
async def get_wallet_balance(
    wallet_id: str,
    chain: str = "base",
    token: str = "USDC",
):
    wallet = await wallet_repo.get(wallet_id)
    balance = await wallet.get_balance(chain, token)  # ✅ From chain
    return {
        "balance": str(balance),
        "chain": chain,
        "token": token,
        "address": wallet.addresses.get(chain),
    }
```

**Action Items:**
- [ ] Update `GET /wallets/{id}/balance` to read from chain
- [ ] Add `chain` and `token` query parameters
- [ ] Remove any balance update endpoints
- [ ] Update API documentation

#### 3.2 Update Payment Execution

**File:** `packages/sardis-api/src/sardis_api/routers/payments.py`

**Before:**
```python
@router.post("/payments/execute")
async def execute_payment(mandate: PaymentMandate):
    wallet = await wallet_repo.get(mandate.subject)
    
    # Check balance (from database)
    if wallet.balance < mandate.amount_minor:
        raise HTTPException(400, "Insufficient balance")
    
    # Update balance (custodial)
    wallet.balance -= mandate.amount_minor
    await wallet_repo.save(wallet)
    
    # Execute transaction
    result = await chain_executor.execute(mandate)
    return result
```

**After:**
```python
@router.post("/payments/execute")
async def execute_payment(mandate: PaymentMandate):
    wallet = await wallet_repo.get(mandate.subject)
    
    # Policy check (includes on-chain balance check)
    policy_result = await policy_engine.evaluate(
        wallet=wallet,
        amount=mandate.amount_minor,
        merchant_id=mandate.destination,
        chain=mandate.chain,
        token=mandate.token,
    )
    
    if not policy_result.approved:
        raise HTTPException(403, policy_result.reason)
    
    # Sign transaction (non-custodial)
    signed_tx = await wallet.sign_transaction(
        chain=mandate.chain,
        to=mandate.destination,
        amount=mandate.amount_minor,
        token=mandate.token,
    )
    
    # Execute on-chain
    result = await chain_executor.execute(signed_tx)
    return result
```

**Action Items:**
- [ ] Remove balance update logic
- [ ] Use policy engine for balance checks
- [ ] Use wallet.sign_transaction() instead of direct transfer
- [ ] Update error handling

---

### Phase 4: SDK Updates

#### 4.1 Python SDK

**File:** `packages/sardis-sdk-python/src/sardis_sdk/resources/wallets.py`

**Before:**
```python
class WalletsResource:
    async def get_balance(self, wallet_id: str) -> Decimal:
        response = await self._client.get(f"/wallets/{wallet_id}/balance")
        return Decimal(response["balance"])  # ❌ From database
```

**After:**
```python
class WalletsResource:
    async def get_balance(
        self,
        wallet_id: str,
        chain: str = "base",
        token: str = "USDC",
    ) -> Decimal:
        response = await self._client.get(
            f"/wallets/{wallet_id}/balance",
            params={"chain": chain, "token": token},
        )
        return Decimal(response["balance"])  # ✅ From chain
    
    async def get_addresses(self, wallet_id: str) -> dict[str, str]:
        """Get wallet addresses for all chains."""
        response = await self._client.get(f"/wallets/{wallet_id}/addresses")
        return response["addresses"]
```

**Action Items:**
- [ ] Update `get_balance()` to include chain/token params
- [ ] Add `get_addresses()` method
- [ ] Remove any balance update methods
- [ ] Update examples

#### 4.2 TypeScript SDK

**File:** `packages/sardis-sdk-js/src/resources/wallets.ts`

Similar changes as Python SDK.

**Action Items:**
- [ ] Update `getBalance()` method
- [ ] Add `getAddresses()` method
- [ ] Update TypeScript types
- [ ] Update examples

---

### Phase 5: Documentation Updates

#### 5.1 Update README

**File:** `README.md`

**Changes:**
- Update "How It Works" section to reflect non-custodial model
- Remove references to "holding funds"
- Add note: "Sardis never holds funds. Wallets are sign-only."

#### 5.2 Update API Documentation

**File:** `docs/api-reference.md`

**Changes:**
- Update wallet endpoints documentation
- Add chain/token parameters to balance endpoints
- Remove balance update endpoints
- Add note about non-custodial architecture

#### 5.3 Update Architecture Documentation

**File:** `docs/architecture.md`

**Changes:**
- Add section on non-custodial architecture
- Explain MPC signing flow
- Document balance reading from chain

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_wallets.py`

**Updates:**
- Remove balance-related tests
- Add tests for `get_balance()` (mocked chain calls)
- Add tests for `sign_transaction()`
- Add tests for address management

### Integration Tests

**File:** `tests/integration/test_payment_flow.py`

**Updates:**
- Update to use policy engine for balance checks
- Mock chain balance queries
- Test sign-only transaction flow

---

## Migration Script

### Database Migration

**File:** `migrations/003_remove_custodial_balance.sql`

```sql
-- Migration: Remove custodial balance columns

BEGIN;

-- Add new columns
ALTER TABLE wallets
    ADD COLUMN mpc_provider VARCHAR,
    ADD COLUMN addresses JSONB;

-- Migrate existing data (if any)
-- Note: This assumes existing wallets have addresses
UPDATE wallets
SET mpc_provider = 'turnkey',
    addresses = jsonb_build_object(
        'base', COALESCE((metadata->>'base_address'), ''),
        'polygon', COALESCE((metadata->>'polygon_address'), '')
    )
WHERE addresses IS NULL;

-- Remove old columns
ALTER TABLE wallets
    DROP COLUMN balance,
    DROP COLUMN token_balances,
    DROP COLUMN spent_total;

-- Make new columns required
ALTER TABLE wallets
    ALTER COLUMN mpc_provider SET NOT NULL;

COMMIT;
```

---

## Rollback Plan

If migration needs to be rolled back:

1. **Database:**
   - Restore from backup
   - Or re-add balance columns with default values

2. **Code:**
   - Revert to previous commit
   - Or use feature flag to toggle between custodial/non-custodial

3. **Deployment:**
   - Deploy previous version
   - Monitor for issues

---

## Success Criteria

Migration is complete when:

- [ ] All balance storage removed from codebase
- [ ] All balance reads come from chain (not database)
- [ ] All wallet operations are sign-only
- [ ] Policy engine handles balance checks
- [ ] API endpoints updated
- [ ] SDKs updated
- [ ] Documentation updated
- [ ] Tests passing
- [ ] Database migration complete

---

## Timeline

- **Week 1:** Wallet model refactoring
- **Week 2:** Policy engine updates
- **Week 3:** API endpoint updates
- **Week 4:** SDK updates + documentation
- **Week 5:** Testing + migration script
- **Week 6:** Deployment + monitoring

---

**Document Status:** Implementation Guide  
**Last Updated:** January 11, 2026
