# Sardis API Server
# Production-ready Docker image

FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy all package definitions
COPY pyproject.toml ./
COPY sardis/ sardis/
COPY packages/ packages/

# Install all packages in dependency order
RUN pip install --no-cache-dir \
    -e packages/sardis-core \
    -e packages/sardis-protocol \
    -e packages/sardis-chain \
    -e packages/sardis-ledger \
    -e packages/sardis-wallet \
    -e packages/sardis-compliance \
    -e packages/sardis-cards \
    -e packages/sardis-checkout \
    -e packages/sardis-ramp \
    -e packages/sardis-ucp \
    -e packages/sardis-a2a \
    -e packages/sardis-api \
    -e .

# Install additional runtime dependencies
RUN pip install --no-cache-dir \
    uvicorn>=0.23.0 \
    gunicorn>=21.2.0 \
    PyJWT>=2.8 \
    redis>=5.0 \
    PyNaCl>=1.5 \
    cryptography>=41.0 \
    apscheduler>=3.10 \
    sentry-sdk[fastapi]>=2.0 \
    prometheus-client>=0.19 \
    alembic>=1.13 \
    httpx>=0.26.0

# --- Production stage ---
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Create non-root user
RUN groupadd -r sardis && useradd -r -g sardis sardis && \
    chown -R sardis:sardis /app

USER sardis

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os; import httpx; r = httpx.get(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/health'); r.raise_for_status()" || exit 1

EXPOSE 8000 10000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SARDIS_API_HOST=0.0.0.0 \
    SARDIS_API_PORT=8000 \
    PORT=8000

# Run with gunicorn + uvicorn workers for production
# Uses $PORT env var (Render sets PORT=10000, default 8000)
CMD gunicorn sardis_api.main:create_app \
    --factory \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --bind "0.0.0.0:${PORT}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile -
