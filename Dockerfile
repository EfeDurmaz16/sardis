# Multi-stage build for Sardis FastAPI backend
# Stage 1: Builder
FROM python:3.12-slim AS builder

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
RUN /app/.venv/bin/pip install --no-cache-dir \
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
FROM python:3.12-slim

WORKDIR /app

# Install runtime tools
RUN pip install --no-cache-dir uv "uvicorn[standard]"

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

# Run the FastAPI application with monorepo package sources on PYTHONPATH.
CMD PYTHONPATH="$(find /app/packages -type d -name src | tr '\n' ':')${PYTHONPATH:+:$PYTHONPATH}" uvicorn sardis_api.main:create_app --factory --host 0.0.0.0 --port ${PORT}
