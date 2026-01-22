# =============================================================================
# Sardis API - Production Dockerfile
# =============================================================================
#
# Multi-stage build for minimal production image
#
# Build: docker build -t sardis-api .
# Run:   docker run -p 8000:8000 --env-file .env sardis-api
#
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and build wheels
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY pyproject.toml ./

# Install base dependencies first (for better caching)
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install the package with all dependencies
# Note: This assumes sardis-core and other packages are available
# In production, use a requirements.txt or pip install from registry
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Install additional production dependencies
RUN pip install --no-cache-dir \
    uvicorn[standard] \
    gunicorn \
    asyncpg \
    httpx \
    redis


# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim as runtime

# Security: Run as non-root user
RUN useradd --create-home --shell /bin/bash sardis
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=sardis:sardis src/ ./src/
COPY --chown=sardis:sardis scripts/ ./scripts/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SARDIS_ENVIRONMENT=production \
    PORT=8000

# Switch to non-root user
USER sardis

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run with gunicorn for production
# Workers = (2 * CPU cores) + 1, but we use env var for flexibility
CMD ["sh", "-c", "gunicorn sardis_api.main:create_app --factory -w ${GUNICORN_WORKERS:-4} -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT} --access-logfile - --error-logfile - --capture-output"]


# -----------------------------------------------------------------------------
# Stage 3: Development image (optional)
# -----------------------------------------------------------------------------
FROM runtime as development

# Switch back to root to install dev dependencies
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    httpx \
    black \
    ruff \
    mypy

# Switch back to non-root
USER sardis

# Use uvicorn for development (auto-reload)
CMD ["uvicorn", "sardis_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]
