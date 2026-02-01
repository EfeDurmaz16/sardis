# Sardis API Server
# Multi-stage build for production deployment

FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./
COPY packages/sardis-core/pyproject.toml packages/sardis-core/
COPY packages/sardis-api/pyproject.toml packages/sardis-api/
COPY packages/sardis-chain/pyproject.toml packages/sardis-chain/
COPY packages/sardis-protocol/pyproject.toml packages/sardis-protocol/
COPY packages/sardis-wallet/pyproject.toml packages/sardis-wallet/
COPY packages/sardis-ledger/pyproject.toml packages/sardis-ledger/
COPY packages/sardis-compliance/pyproject.toml packages/sardis-compliance/
COPY packages/sardis-checkout/pyproject.toml packages/sardis-checkout/

# Install dependencies
RUN uv sync --no-dev --no-install-project 2>/dev/null || pip install --no-cache-dir \
    fastapi>=0.115.0 \
    uvicorn>=0.23.0 \
    asyncpg>=0.30.0 \
    pydantic>=2.0.0 \
    httpx>=0.24.0 \
    python-multipart>=0.0.22

# Copy application code
FROM base AS app

COPY packages/ packages/
COPY sardis/ sardis/

# Install the project packages
RUN uv sync --no-dev 2>/dev/null || pip install --no-cache-dir \
    -e packages/sardis-core \
    -e packages/sardis-api \
    -e packages/sardis-chain \
    -e packages/sardis-protocol \
    -e packages/sardis-wallet \
    -e packages/sardis-ledger \
    -e packages/sardis-compliance \
    -e packages/sardis-checkout

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Copy installed packages from build stage
COPY --from=app /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=app /usr/local/bin /usr/local/bin
COPY --from=app /app /app

# Create non-root user
RUN groupadd -r sardis && useradd -r -g sardis sardis
USER sardis

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/api/v2/health'); r.raise_for_status()" || exit 1

EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "sardis_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
