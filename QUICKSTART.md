# Sardis Quick Start Guide

Get Sardis running locally in 5 minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (optional, SQLite works for dev)

## 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/sardis.git
cd sardis

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -e sardis-core/
pip install -e sardis-protocol/
pip install -e sardis-wallet/
pip install -e sardis-chain/
pip install -e sardis-ledger/
pip install -e sardis-compliance/
pip install -e sardis-api/

# Install dashboard dependencies
cd dashboard
npm install
cd ..
```

## 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings (optional for dev)
# For local dev, defaults work fine
```

## 3. Start the API

```bash
# Terminal 1: Start the API server
cd sardis-api
uvicorn sardis_api.main:create_app --factory --reload --port 8000
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## 4. Start the Dashboard

```bash
# Terminal 2: Start the dashboard
cd dashboard
npm run dev
```

Open http://localhost:3000 in your browser.

## 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/api/v2/docs
```

## Using PostgreSQL (Production)

### Option A: Neon (Recommended for demo)

1. Create a free account at https://neon.tech
2. Create a new project
3. Copy the connection string
4. Set in `.env`:
   ```
   DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/sardis?sslmode=require
   ```

### Option B: Local PostgreSQL

```bash
# Create database
createdb sardis

# Set in .env
DATABASE_URL=postgresql://localhost/sardis
```

### Initialize and Seed

```bash
# Initialize schema and seed demo data
python scripts/seed_demo.py --init-schema

# Output will include a demo API key - save it!
```

## Deploy to Vercel

### Dashboard Only

```bash
cd dashboard
vercel
```

### Full Stack (Dashboard + API)

```bash
# From project root
vercel

# Set environment variables in Vercel dashboard:
# - DATABASE_URL
# - SARDIS_SECRET_KEY
# - SARDIS_ALLOWED_ORIGINS
```

## Common Issues

### "Module not found" errors

Make sure all packages are installed in editable mode:
```bash
pip install -e sardis-core/ -e sardis-protocol/ -e sardis-wallet/ -e sardis-chain/ -e sardis-ledger/ -e sardis-compliance/ -e sardis-api/
```

### CORS errors in browser

Check that your frontend URL is in `SARDIS_ALLOWED_ORIGINS`:
```
SARDIS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Database connection errors

For local dev without PostgreSQL, the API will use SQLite automatically.

## Next Steps

1. **Explore the API**: http://localhost:8000/api/v2/docs
2. **Create an agent**: Use the dashboard or API
3. **Execute a payment**: Try the AP2 payment flow
4. **Set up webhooks**: Configure event notifications

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐
│    Dashboard    │────▶│   Sardis API    │
│   (React/Vite)  │     │   (FastAPI)     │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Wallet   │ │ Protocol │ │  Chain   │
              │ Manager  │ │ Verifier │ │ Executor │
              └──────────┘ └──────────┘ └──────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                         ┌──────────────┐
                         │  PostgreSQL  │
                         │   (Ledger)   │
                         └──────────────┘
```

## Support

- Documentation: See `NEWPLAN.md` for architecture details
- Issues: GitHub Issues
- Status: See `IMPLEMENTATION_STATUS.md`
