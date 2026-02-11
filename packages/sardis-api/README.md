# sardis-api

[![PyPI version](https://badge.fury.io/py/sardis-api.svg)](https://badge.fury.io/py/sardis-api)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

FastAPI gateway for Sardis stablecoin execution.

## Overview

`sardis-api` provides a production-ready REST API for the Sardis payment infrastructure:

- **Mandate Processing**: AP2 Intent/Cart/Payment mandate ingestion and verification
- **Wallet Operations**: Orchestration, approvals, and balance queries
- **Ledger Access**: Transaction history and compliance feeds
- **Agent Management**: AI agent registration, policies, and spending controls
- **Compliance Integration**: KYC/AML hooks and sanction screening

## Installation

```bash
pip install sardis-api
```

### Development Installation

```bash
pip install sardis-api[dev]
```

## Quick Start

```python
import uvicorn
from sardis_api import create_app

# Create the FastAPI application
app = create_app()

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Or use the CLI:

```bash
uvicorn sardis_api.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Wallets

```
POST   /api/v2/wallets              Create a new wallet
GET    /api/v2/wallets/{wallet_id}  Get wallet details
GET    /api/v2/wallets/{wallet_id}/balance  Get wallet balance
```

### Transactions

```
POST   /api/v2/transactions         Initiate a transaction
GET    /api/v2/transactions/{tx_id} Get transaction status
GET    /api/v2/wallets/{wallet_id}/transactions  List wallet transactions
```

### Agents

```
POST   /api/v2/agents               Register an AI agent
GET    /api/v2/agents/{agent_id}    Get agent details
PATCH  /api/v2/agents/{agent_id}/policy  Update agent policy
```

### Mandates

```
POST   /api/v2/mandates/intent      Submit an intent mandate
POST   /api/v2/mandates/cart        Submit a cart mandate
POST   /api/v2/mandates/payment     Submit a payment mandate
```

### Holds

```
POST   /api/v2/holds                Create a payment hold
POST   /api/v2/holds/{hold_id}/capture  Capture a hold
POST   /api/v2/holds/{hold_id}/void     Void a hold
```

## Configuration

Configure via environment variables:

```bash
# Database
SARDIS_DATABASE_URL=postgresql://user:pass@localhost/sardis

# Redis (for caching and rate limiting)
SARDIS_REDIS_URL=redis://localhost:6379

# API Settings
SARDIS_API_HOST=0.0.0.0
SARDIS_API_PORT=8000
SARDIS_API_CORS_ORIGINS=["http://localhost:3000"]

# Security
SARDIS_API_KEY_HEADER=X-API-Key
SARDIS_JWT_SECRET=your-secret-key
```

## Middleware

The API includes production-ready middleware:

- **Authentication**: API key and JWT validation
- **Rate Limiting**: Per-client request throttling
- **Logging**: Structured request/response logging
- **Security**: CORS, security headers, input validation
- **Exception Handling**: Consistent error responses

## OpenAPI Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Architecture

```
sardis-api/
├── main.py           # Application entry point
├── dependencies.py   # FastAPI dependencies
├── routers/
│   ├── wallets.py    # Wallet endpoints
│   ├── transactions.py
│   ├── agents.py
│   ├── mandates.py
│   ├── holds.py
│   └── ...
└── middleware/
    ├── auth.py       # Authentication
    ├── rate_limit.py # Rate limiting
    ├── logging.py    # Request logging
    └── security.py   # Security headers
```

## Requirements

- Python 3.11+
- FastAPI >= 0.109
- uvicorn >= 0.23
- sardis-core >= 0.1.0
- sardis-ledger >= 0.1.0
- sardis-chain >= 0.1.0
- sardis-compliance >= 0.1.0

## Documentation

Full documentation is available at [docs.sardis.sh/api](https://docs.sardis.sh/api).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.
