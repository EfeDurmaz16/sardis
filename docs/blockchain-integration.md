# Blockchain Integration Guide

## Overview

This document outlines the strategy for integrating Sardis with real blockchain networks for production deployment. It covers wallet management approaches, on-chain settlement, gas optimization, and cross-chain bridging.

## Wallet Architecture Options

### Option 1: MPC Wallets (Recommended)

**Multi-Party Computation (MPC)** splits the private key into multiple shares, requiring a threshold of shares to sign transactions.

```
┌─────────────────────────────────────────────────────────────┐
│                    MPC WALLET ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│   │  Share 1 │   │  Share 2 │   │  Share 3 │               │
│   │ (Sardis) │   │ (Client) │   │  (HSM)   │               │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘               │
│        │              │              │                      │
│        └──────────────┼──────────────┘                      │
│                       │                                      │
│                       ▼                                      │
│              ┌────────────────┐                             │
│              │  MPC Protocol  │                             │
│              │  (2-of-3 TSS)  │                             │
│              └────────────────┘                             │
│                       │                                      │
│                       ▼                                      │
│              ┌────────────────┐                             │
│              │   Signature    │ ──────► Blockchain          │
│              └────────────────┘                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Advantages:**
- No single point of compromise
- No hot wallet with full private key
- Supports policy-based signing (spending limits)
- Recovery possible with threshold shares

**Recommended Providers:**
| Provider | Features | Pricing Model |
|----------|----------|---------------|
| Fireblocks | Enterprise MPC, DeFi access | Per-wallet + transaction |
| Fordefi | Policy engine, EVM focus | Subscription |
| ZenGo | Consumer MPC, mobile SDK | Per-wallet |
| Lit Protocol | Decentralized MPC | Pay-per-use |

**Implementation:**

```python
from fireblocks_sdk import FireblocksSDK

class MPCWalletService:
    """MPC wallet management via Fireblocks."""
    
    def __init__(self, api_key: str, api_secret: str):
        self.fb = FireblocksSDK(api_secret, api_key)
    
    async def create_wallet(self, agent_id: str) -> str:
        """Create a new MPC vault for an agent."""
        vault = self.fb.create_vault_account(
            name=f"sardis_agent_{agent_id}",
            customer_ref_id=agent_id,
            auto_fuel=True
        )
        
        # Create wallet for each supported asset
        for asset in ["USDC", "USDT"]:
            self.fb.create_vault_asset(vault["id"], asset)
        
        return vault["id"]
    
    async def sign_transaction(
        self,
        vault_id: str,
        asset: str,
        destination: str,
        amount: str
    ) -> str:
        """Sign and broadcast a transaction."""
        tx = self.fb.create_transaction(
            asset_id=asset,
            source={
                "type": "VAULT_ACCOUNT",
                "id": vault_id
            },
            destination={
                "type": "ONE_TIME_ADDRESS",
                "oneTimeAddress": {"address": destination}
            },
            amount=amount
        )
        return tx["id"]
```

### Option 2: Custodial Wallets

Sardis holds all private keys in a secure enclave, managing custody on behalf of agents.

```
┌─────────────────────────────────────────────────────────────┐
│                  CUSTODIAL ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    Sardis Backend                       │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐       │ │
│  │  │   Agent    │  │   Wallet   │  │   Key      │       │ │
│  │  │  Service   │──│  Service   │──│  Vault     │       │ │
│  │  └────────────┘  └────────────┘  └────────────┘       │ │
│  │                                          │              │ │
│  │                                          ▼              │ │
│  │                                   ┌────────────┐       │ │
│  │                                   │    HSM     │       │ │
│  │                                   │ (AWS/GCP)  │       │ │
│  │                                   └────────────┘       │ │
│  └────────────────────────────────────────────────────────┘ │
│                              │                               │
│                              ▼                               │
│                    ┌──────────────────┐                     │
│                    │   Blockchains    │                     │
│                    └──────────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Advantages:**
- Simpler integration
- Full control over UX
- Lower per-transaction costs

**Disadvantages:**
- Single point of failure (Sardis)
- Regulatory complexity (custody)
- Higher liability

**Implementation:**

```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import boto3

class CustodialWalletService:
    """Custodial wallet using AWS KMS."""
    
    def __init__(self):
        self.kms = boto3.client('kms')
        self.key_store = {}  # In production: encrypted database
    
    async def create_wallet(self, agent_id: str, chain: str) -> str:
        """Create a new custodial wallet."""
        # Create CMK for this agent
        key = self.kms.create_key(
            Description=f"Sardis wallet key for {agent_id}",
            KeyUsage='SIGN_VERIFY',
            KeySpec='ECC_SECG_P256K1',  # secp256k1 for EVM
            Tags=[
                {'TagKey': 'agent_id', 'TagValue': agent_id},
                {'TagKey': 'chain', 'TagValue': chain}
            ]
        )
        
        # Derive address from public key
        public_key = self.kms.get_public_key(KeyId=key['KeyMetadata']['KeyId'])
        address = self._derive_address(public_key['PublicKey'])
        
        self.key_store[agent_id] = {
            'key_id': key['KeyMetadata']['KeyId'],
            'address': address,
            'chain': chain
        }
        
        return address
    
    async def sign_transaction(self, agent_id: str, tx_hash: bytes) -> bytes:
        """Sign a transaction hash using KMS."""
        key_info = self.key_store[agent_id]
        
        response = self.kms.sign(
            KeyId=key_info['key_id'],
            Message=tx_hash,
            MessageType='DIGEST',
            SigningAlgorithm='ECDSA_SHA_256'
        )
        
        return response['Signature']
```

### Option 3: Hybrid Approach

Combine MPC for high-value operations with custodial for low-value, high-frequency transactions.

```
Transaction Amount Decision Tree:
─────────────────────────────────
         │
    Amount > $1000?
    ┌────┴────┐
   YES       NO
    │         │
    ▼         ▼
  MPC      Custodial
Signing    Signing
(2-of-3)   (Single)
```

## Key Management

### Hierarchical Deterministic (HD) Wallets

Use BIP-44 derivation for organized key management:

```
Master Seed
    │
    └── m/44'/60'/0'  (Ethereum)
        ├── /0/0  → Agent 1 Wallet
        ├── /0/1  → Agent 2 Wallet
        └── /0/N  → Agent N Wallet
```

**Benefits:**
- Single backup restores all wallets
- Deterministic address generation
- Organized key hierarchy

### Key Rotation

```python
class KeyRotationPolicy:
    """Automated key rotation for enhanced security."""
    
    ROTATION_INTERVAL_DAYS = 90
    
    async def should_rotate(self, wallet_id: str) -> bool:
        """Check if wallet needs key rotation."""
        last_rotation = await self.get_last_rotation(wallet_id)
        days_since = (datetime.now() - last_rotation).days
        return days_since >= self.ROTATION_INTERVAL_DAYS
    
    async def rotate_keys(self, wallet_id: str):
        """Perform key rotation."""
        # 1. Generate new key pair
        new_address = await self.create_new_wallet(wallet_id)
        
        # 2. Transfer all assets to new address
        await self.migrate_assets(wallet_id, new_address)
        
        # 3. Update wallet mapping
        await self.update_wallet_address(wallet_id, new_address)
        
        # 4. Archive old key (keep for audit)
        await self.archive_old_key(wallet_id)
```

## On-Chain Settlement Flow

### Real-Time Settlement

```
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│ Agent  │    │ Sardis │    │ Wallet │    │  RPC   │    │ Chain  │
│  SDK   │    │  API   │    │Service │    │Provider│    │        │
└───┬────┘    └───┬────┘    └───┬────┘    └───┬────┘    └───┬────┘
    │             │             │             │             │
    │ pay()       │             │             │             │
    │────────────>│             │             │             │
    │             │ validate    │             │             │
    │             │────────────>│             │             │
    │             │             │ build tx    │             │
    │             │             │────────────>│             │
    │             │             │             │ broadcast   │
    │             │             │             │────────────>│
    │             │             │             │<────────────│
    │             │             │             │  tx_hash    │
    │             │             │<────────────│             │
    │             │<────────────│             │             │
    │<────────────│  pending    │             │             │
    │             │             │             │             │
    │             │             │ poll status │             │
    │             │             │────────────>│             │
    │             │             │<────────────│ confirmed   │
    │             │<────────────│             │             │
    │<────────────│  completed  │             │             │
```

### Batched Settlement

For high-volume, low-value transactions, batch multiple payments:

```python
class BatchSettlement:
    """Batch multiple payments into single on-chain transaction."""
    
    BATCH_SIZE = 100
    BATCH_INTERVAL_SECONDS = 60
    
    def __init__(self):
        self.pending_payments = []
        self.last_batch_time = datetime.now()
    
    async def queue_payment(self, payment: Payment):
        """Add payment to batch queue."""
        self.pending_payments.append(payment)
        
        if self._should_settle():
            await self.settle_batch()
    
    def _should_settle(self) -> bool:
        """Check if batch should be settled."""
        if len(self.pending_payments) >= self.BATCH_SIZE:
            return True
        if (datetime.now() - self.last_batch_time).seconds >= self.BATCH_INTERVAL_SECONDS:
            return True
        return False
    
    async def settle_batch(self):
        """Settle all pending payments in one transaction."""
        if not self.pending_payments:
            return
        
        # Group by destination
        batches = self._group_by_destination()
        
        # Use multicall or batch transfer contract
        for chain, payments in batches.items():
            await self._execute_batch(chain, payments)
        
        self.pending_payments = []
        self.last_batch_time = datetime.now()
```

## Gas Fee Optimization

### Fee Estimation

```python
class GasOptimizer:
    """Optimize gas fees across chains."""
    
    async def estimate_fee(
        self,
        chain: ChainType,
        urgency: str = "normal"
    ) -> GasEstimate:
        """Estimate optimal gas price."""
        
        # Get current gas prices
        if chain in [ChainType.BASE, ChainType.ETHEREUM, ChainType.POLYGON]:
            return await self._estimate_evm_gas(chain, urgency)
        elif chain == ChainType.SOLANA:
            return await self._estimate_solana_priority(urgency)
    
    async def _estimate_evm_gas(self, chain: ChainType, urgency: str):
        """Estimate EVM gas using EIP-1559."""
        
        # Get base fee from latest block
        block = await self.rpc.get_block("latest")
        base_fee = block["baseFeePerGas"]
        
        # Priority fee based on urgency
        priority_fees = {
            "slow": 1_000_000_000,      # 1 gwei
            "normal": 2_000_000_000,    # 2 gwei
            "fast": 5_000_000_000,      # 5 gwei
            "instant": 10_000_000_000,  # 10 gwei
        }
        
        max_priority = priority_fees.get(urgency, priority_fees["normal"])
        max_fee = base_fee * 2 + max_priority
        
        return GasEstimate(
            base_fee=base_fee,
            max_priority_fee=max_priority,
            max_fee=max_fee,
            estimated_cost_usd=self._to_usd(max_fee * 65000, chain)
        )
```

### Gas Abstraction

Allow agents to pay gas in stablecoins:

```python
class GasAbstraction:
    """Pay gas fees in USDC instead of native token."""
    
    async def execute_with_gas_abstraction(
        self,
        agent_id: str,
        transaction: Transaction
    ):
        """Execute transaction with gas paid in USDC."""
        
        # 1. Calculate gas cost in USDC
        gas_estimate = await self.estimate_gas(transaction)
        usdc_cost = await self.convert_to_usdc(
            gas_estimate.cost,
            transaction.chain
        )
        
        # 2. Deduct USDC from agent wallet (internal ledger)
        await self.deduct_gas_fee(agent_id, usdc_cost)
        
        # 3. Use Sardis relayer to pay actual gas
        # (Sardis maintains native token balance for gas)
        signed_tx = await self.sign_transaction(transaction)
        tx_hash = await self.relayer.submit(signed_tx)
        
        return tx_hash
```

## Cross-Chain Bridges

### Bridge Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CROSS-CHAIN BRIDGE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Source Chain (e.g., Ethereum)                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  1. Lock USDC in Bridge Contract                       │ │
│  │     └── emit LockEvent(amount, destination_chain, to)  │ │
│  └────────────────────────────────────────────────────────┘ │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  2. Relayer Network detects LockEvent                  │ │
│  │     └── Validators sign attestation                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                         │                                    │
│                         ▼                                    │
│  Destination Chain (e.g., Solana)                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  3. Release USDC from Bridge Pool                      │ │
│  │     └── Verify signatures, mint/release tokens         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Bridge Integration

```python
class BridgeService:
    """Cross-chain bridge integration."""
    
    # Supported bridge providers
    BRIDGES = {
        ("ethereum", "polygon"): "polygon_bridge",
        ("ethereum", "base"): "base_bridge",
        ("ethereum", "solana"): "wormhole",
        ("polygon", "solana"): "wormhole",
    }
    
    async def bridge_tokens(
        self,
        source_chain: str,
        dest_chain: str,
        token: str,
        amount: Decimal,
        destination_address: str
    ) -> BridgeTransaction:
        """Bridge tokens between chains."""
        
        bridge = self._get_bridge(source_chain, dest_chain)
        
        # Estimate bridge fee and time
        estimate = await bridge.estimate(token, amount)
        
        # Execute bridge
        tx = await bridge.initiate_transfer(
            token=token,
            amount=amount,
            destination=destination_address
        )
        
        return BridgeTransaction(
            bridge_id=tx.id,
            source_chain=source_chain,
            dest_chain=dest_chain,
            amount=amount,
            fee=estimate.fee,
            estimated_time=estimate.time_minutes,
            status="pending"
        )
    
    async def get_bridge_status(self, bridge_tx_id: str) -> str:
        """Check bridge transaction status."""
        # Poll bridge API for status
        pass
```

### Liquidity Management

```
┌─────────────────────────────────────────────────────────────┐
│                 LIQUIDITY POOLS                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Base Pool          Ethereum Pool      Solana Pool         │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐        │
│  │ USDC: 1M │       │ USDC: 2M │       │ USDC: 500K│        │
│  │ USDT: 500K│      │ USDT: 1M │       │ USDT: 200K│        │
│  └──────────┘       └──────────┘       └──────────┘        │
│       │                   │                   │             │
│       └───────────────────┼───────────────────┘             │
│                           │                                  │
│                    Rebalancing Engine                        │
│                           │                                  │
│           ┌───────────────┼───────────────┐                 │
│           │               │               │                  │
│    Low Liquidity?   Excess Liquidity?   Imbalanced?         │
│           │               │               │                  │
│    Bridge IN        Bridge OUT        Rebalance             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## RPC Provider Strategy

### Multi-Provider Failover

```python
class RPCManager:
    """Manage RPC connections with failover."""
    
    PROVIDERS = {
        ChainType.ETHEREUM: [
            ("alchemy", "https://eth-mainnet.g.alchemy.com/v2/{key}"),
            ("infura", "https://mainnet.infura.io/v3/{key}"),
            ("quicknode", "https://eth-mainnet.quiknode.pro/{key}"),
        ],
        ChainType.BASE: [
            ("alchemy", "https://base-mainnet.g.alchemy.com/v2/{key}"),
            ("quicknode", "https://base-mainnet.quiknode.pro/{key}"),
        ],
    }
    
    async def call(self, chain: ChainType, method: str, params: list):
        """Make RPC call with automatic failover."""
        providers = self.PROVIDERS[chain]
        
        for name, url in providers:
            try:
                response = await self._rpc_call(url, method, params)
                return response
            except Exception as e:
                logger.warning(f"RPC {name} failed: {e}")
                continue
        
        raise RPCError(f"All providers failed for {chain}")
```

### Rate Limiting

```python
class RateLimiter:
    """Rate limit RPC calls per provider."""
    
    LIMITS = {
        "alchemy": {"requests_per_second": 25, "compute_units_per_day": 300_000_000},
        "infura": {"requests_per_second": 10, "requests_per_day": 100_000},
    }
    
    def __init__(self):
        self.counters = defaultdict(lambda: {"second": 0, "day": 0})
        self.last_reset = defaultdict(datetime.now)
    
    async def acquire(self, provider: str):
        """Acquire rate limit slot."""
        limits = self.LIMITS[provider]
        
        # Reset counters if needed
        self._maybe_reset(provider)
        
        if self.counters[provider]["second"] >= limits["requests_per_second"]:
            await asyncio.sleep(1)
            self.counters[provider]["second"] = 0
        
        self.counters[provider]["second"] += 1
        self.counters[provider]["day"] += 1
```

## Production Checklist

### Pre-Launch

- [ ] MPC/custodial wallet provider integrated
- [ ] HSM configured for key storage
- [ ] Multi-provider RPC failover tested
- [ ] Gas abstraction working
- [ ] Bridge integrations tested
- [ ] Transaction signing audited
- [ ] Key rotation policy implemented
- [ ] Monitoring and alerting configured

### Security

- [ ] Smart contract audit completed
- [ ] Penetration testing done
- [ ] Rate limiting configured
- [ ] DDoS protection enabled
- [ ] Fraud detection rules active
- [ ] Incident response plan documented

### Compliance

- [ ] Transaction monitoring for AML
- [ ] Geographic restrictions implemented
- [ ] Audit trail for all transactions
- [ ] Key ceremony documented
- [ ] Backup and recovery tested

