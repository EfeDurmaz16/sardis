# Multi-stage build for Sardis FastAPI backend
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast Python package management
RUN pip install --no-cache-dir uv

# Copy workspace files
COPY pyproject.toml uv.lock* ./
COPY sardis/ ./sardis/
COPY packages/ ./packages/

# Install dependencies with uv
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Install uv in runtime stage
RUN pip install --no-cache-dir uv

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

# Run the FastAPI application
# Uses $PORT env var (Render sets PORT=10000, default 8000)
CMD uvicorn sardis_api.main:create_app --factory --host 0.0.0.0 --port ${PORT}
