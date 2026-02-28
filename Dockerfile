# Multi-stage build for Sardis FastAPI backend
# Stage 1: Builder
FROM python:3.14-slim AS builder

WORKDIR /app

# Install uv for fast Python package management
RUN pip install --no-cache-dir uv

# Copy workspace files
COPY pyproject.toml README.md uv.lock* ./
COPY sardis/ ./sardis/
COPY packages/ ./packages/

# Install dependencies with uv
RUN uv sync --frozen --no-dev

# Install monorepo packages (editable) so sardis_api and its transitive deps
# are importable with matching runtime dependencies inside the venv.
RUN uv pip install --python /app/.venv/bin/python \
    -e /app/packages/sardis-core \
    -e /app/packages/sardis-wallet \
    -e /app/packages/sardis-chain \
    -e /app/packages/sardis-protocol \
    -e /app/packages/sardis-ledger \
    -e /app/packages/sardis-cards \
    -e /app/packages/sardis-compliance \
    -e /app/packages/sardis-checkout \
    -e /app/packages/sardis-coinbase \
    -e /app/packages/sardis-ramp \
    -e /app/packages/sardis-api

# Stage 2: Runtime
FROM python:3.14-slim

WORKDIR /app

# Install runtime tools
RUN pip install --no-cache-dir uv "uvicorn[standard]" gunicorn

# Copy installed dependencies and source code from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/sardis /app/sardis
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Create non-root user
RUN groupadd -r sardis && useradd -r -g sardis sardis && \
    chown -R sardis:sardis /app

USER sardis

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SARDIS_ENVIRONMENT=production \
    SARDIS_API_HOST=0.0.0.0 \
    SARDIS_API_PORT=8000 \
    PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run with gunicorn + uvicorn workers for production concurrency.
# SARDIS_WORKERS defaults to 4; set to 1 for development or memory-constrained environments.
CMD PYTHONPATH="$(find /app/packages -type d -name src | tr '\n' ':')${PYTHONPATH:+:$PYTHONPATH}" \
    gunicorn sardis_api.main:create_app \
    --factory \
    -w ${SARDIS_WORKERS:-4} \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:${PORT} \
    --access-logfile - \
    --error-logfile - \
    --capture-output
