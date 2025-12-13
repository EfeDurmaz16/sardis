# Sardis Production Deployment Plan

> **Goal**: Transform Sardis from simulation to a real payment system
> **Estimated Time**: 2-3 weeks
> **Status**: 🚀 Ready to Execute

---

## Phase 1: Infrastructure Setup (Days 1-3)

### 1.1 Database (PostgreSQL)

**Option A: Neon (Recommended for Serverless)**
```bash
# 1. Create account at https://neon.tech
# 2. Create project "sardis-production"
# 3. Get connection string

export DATABASE_URL="postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/sardis?sslmode=require"
```

**Option B: Supabase**
```bash
# 1. Create project at https://supabase.com
# 2. Get connection string from Settings > Database
```

**Initialize Schema**:
```bash
# Install sardis packages
pip install -e sardis-core sardis-api sardis-chain sardis-protocol sardis-wallet sardis-ledger sardis-compliance

# Initialize database
python scripts/seed_demo.py --init-schema
python scripts/seed_demo.py
```

### 1.2 Redis (Optional - for Rate Limiting)

```bash
# Option A: Upstash (serverless)
# Create at https://upstash.com
export SARDIS_REDIS_URL="redis://default:xxx@xxx.upstash.io:6379"

# Option B: Skip for now (uses in-memory)
```

### 1.3 Environment Variables

Create `.env.production`:
```bash
# Core
SARDIS_ENVIRONMENT=prod
SARDIS_SECRET_KEY=$(openssl rand -base64 32)

# Database
DATABASE_URL=postgresql://...

# Chain Execution - START WITH SIMULATED
SARDIS_CHAIN_MODE=simulated

# CORS
SARDIS_ALLOWED_ORIGINS=https://your-dashboard.vercel.app,https://api.sardis.network
```

---

## Phase 2: Smart Contract Deployment (Days 4-5)

### 2.1 Get Testnet ETH

```bash
# Base Sepolia Faucet
# https://faucet.quicknode.com/base/sepolia

# Or use Alchemy faucet
# https://sepoliafaucet.com
```

### 2.2 Deploy Contracts

```bash
cd contracts

# Install Foundry (if not installed)
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Install dependencies
forge install OpenZeppelin/openzeppelin-contracts --no-commit

# Set environment
export PRIVATE_KEY="your_deployer_private_key"  # Without 0x
export BASE_SEPOLIA_RPC_URL="https://sepolia.base.org"
export BASESCAN_API_KEY="your_basescan_api_key"

# Deploy to Base Sepolia
forge script script/Deploy.s.sol:DeployTestnet \
    --rpc-url base_sepolia \
    --broadcast \
    --verify

# Note the deployed addresses:
# SardisWalletFactory: 0x...
# SardisEscrow: 0x...
```

### 2.3 Update Contract Addresses

Edit `sardis-chain/src/sardis_chain/executor.py`:
```python
SARDIS_CONTRACTS = {
    "base_sepolia": {
        "wallet_factory": "0x...",  # Your deployed address
        "escrow": "0x...",          # Your deployed address
    },
}
```

---

## Phase 3: MPC Wallet Setup (Days 6-8)

### 3.1 Turnkey Setup (Recommended)

1. **Create Account**: https://app.turnkey.com
2. **Create Organization**
3. **Generate API Keys**:
   - Go to Settings → API Keys
   - Create new key pair
   - Download private key securely

4. **Create Wallet**:
```bash
# Using Turnkey CLI
turnkey wallets create --name "sardis-agent-wallet-1"
```

5. **Set Environment**:
```bash
export TURNKEY_ORGANIZATION_ID="org_..."
export TURNKEY_API_PUBLIC_KEY="..."
export TURNKEY_API_PRIVATE_KEY_FILE="/path/to/private-key.pem"
```

### 3.2 Update Configuration

```python
# In sardis_v2_core/config.py - already configured
mpc:
  name: turnkey
  api_base: https://api.turnkey.com
  credential_id: $TURNKEY_ORGANIZATION_ID
```

---

## Phase 4: Testnet USDC (Days 9-10)

### 4.1 Get Test USDC on Base Sepolia

**Option A: Circle Faucet**
- https://faucet.circle.com/
- Connect wallet, select Base Sepolia, request USDC

**Option B: Mint from Contract**
```bash
# Base Sepolia USDC is at: 0x036CbD53842c5426634e7929541eC2318f3dCF7e
# It may have a public mint function for testing
```

### 4.2 Fund Your MPC Wallet

```bash
# Transfer USDC to your Turnkey wallet address
# You'll need both:
# - ETH for gas
# - USDC for testing
```

---

## Phase 5: End-to-End Test (Days 11-12)

### 5.1 Enable Live Mode

```bash
# Change from simulated to live
export SARDIS_CHAIN_MODE=live
```

### 5.2 Test Transaction

```python
import asyncio
from sardis_sdk import SardisClient

async def test_real_payment():
    async with SardisClient(
        base_url="http://localhost:8000",
        api_key="sk_demo_...",
    ) as client:
        # Create a small test payment
        result = await client.payments.execute_mandate({
            "mandate_id": "test_001",
            "issuer": "test_user",
            "subject": "wallet_agent_alice",  # Your funded wallet
            "destination": "0x742d35Cc6634C0532925a3b844Bc9e7595f8fDB1",  # Test address
            "amount_minor": 100,  # 1 USDC (in cents)
            "token": "USDC",
            "chain": "base_sepolia",
            "expires_at": int(time.time()) + 300,
        })
        
        print(f"Transaction hash: {result.chain_tx_hash}")
        print(f"View on explorer: https://sepolia.basescan.org/tx/{result.chain_tx_hash}")

asyncio.run(test_real_payment())
```

### 5.3 Verify on Block Explorer

- Go to https://sepolia.basescan.org
- Search for your transaction hash
- Confirm it's a real USDC transfer

---

## Phase 6: API Deployment (Days 13-14)

### 6.1 Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd /path/to/sardis
vercel

# Set environment variables
vercel env add DATABASE_URL
vercel env add SARDIS_SECRET_KEY
vercel env add SARDIS_CHAIN_MODE
# ... add all production env vars
```

### 6.2 Custom Domain (Optional)

```bash
# In Vercel dashboard:
# Settings → Domains → Add "api.sardis.network"
```

### 6.3 Verify Deployment

```bash
curl https://api.sardis.network/health
```

---

## Phase 7: Dashboard Deployment (Days 15-16)

```bash
cd dashboard

# Install dependencies
npm install

# Build
npm run build

# Deploy to Vercel
vercel
```

---

## Production Checklist

### Security
- [ ] Secret key is random 32+ bytes
- [ ] Database URL uses SSL
- [ ] API keys are hashed (SHA256)
- [ ] CORS is restricted to known domains
- [ ] Rate limiting is enabled

### Monitoring
- [ ] Datadog or similar APM configured
- [ ] Error alerts set up
- [ ] Transaction monitoring dashboard

### Compliance
- [ ] Persona KYC configured (for production)
- [ ] Elliptic sanctions screening enabled
- [ ] Transaction limits enforced

### Backup
- [ ] Database backups configured
- [ ] Private keys stored securely (never in code)
- [ ] Recovery procedures documented

---

## Quick Start Commands

```bash
# 1. Clone and setup
git clone https://github.com/your-org/sardis.git
cd sardis
python -m venv venv && source venv/bin/activate
pip install -e sardis-core -e sardis-api -e sardis-chain \
            -e sardis-protocol -e sardis-wallet -e sardis-ledger \
            -e sardis-compliance -e sardis-sdk-python

# 2. Set environment
export DATABASE_URL="postgresql://..."
export SARDIS_SECRET_KEY="..."
export SARDIS_CHAIN_MODE="simulated"  # Start with simulated

# 3. Initialize database
python scripts/seed_demo.py --init-schema
python scripts/seed_demo.py

# 4. Start API locally
uvicorn sardis_api.main:create_app --factory --port 8000

# 5. Test
curl http://localhost:8000/health

# 6. When ready for real transactions
export SARDIS_CHAIN_MODE="live"
```

---

## Cost Estimates

| Service | Free Tier | Production |
|---------|-----------|------------|
| **Neon PostgreSQL** | 0.5GB free | ~$20/mo |
| **Vercel** | Free for hobby | ~$20/mo (Pro) |
| **Upstash Redis** | 10K commands/day free | ~$10/mo |
| **Turnkey MPC** | Contact for pricing | ~$500-2000/mo |
| **Base Sepolia Gas** | Free (testnet) | ~$50/mo (mainnet) |
| **Total (Testnet)** | **$0** | - |
| **Total (Mainnet)** | - | **~$600-2000/mo** |

---

## Timeline Summary

| Week | Focus | Milestone |
|------|-------|-----------|
| **Week 1** | Infrastructure + Contracts | DB live, contracts deployed |
| **Week 2** | MPC + Testing | First real testnet transaction |
| **Week 3** | Deployment + Polish | API live, ready for users |

---

## Next Steps After Testnet

1. **Security Audit** - Engage Trail of Bits or OpenZeppelin
2. **Mainnet Contracts** - Deploy to Base mainnet
3. **Real USDC** - Fund production wallets
4. **KYC Integration** - Enable Persona for user verification
5. **Public Launch** - Open to developers

---

## Support Resources

- **Turnkey Docs**: https://docs.turnkey.com
- **Base Docs**: https://docs.base.org
- **Foundry Book**: https://book.getfoundry.sh
- **Circle USDC**: https://developers.circle.com/stablecoins/docs





