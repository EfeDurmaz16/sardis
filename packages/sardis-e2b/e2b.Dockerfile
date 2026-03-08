FROM e2b/base:latest

# Install Python dependencies: Sardis SDK + httpx for HTTP operations
RUN pip install "sardis>=1.0.0" httpx

# Set environment for simulation mode by default
ENV SARDIS_SIMULATION=true

# Copy the sardis_e2b helper package into the sandbox
COPY sardis_e2b/ /opt/sardis_e2b/
ENV PYTHONPATH="/opt:${PYTHONPATH}"

# Add a healthcheck script that verifies the SDK is importable
RUN cat <<'HEALTHCHECK' > /usr/local/bin/sardis-healthcheck && chmod +x /usr/local/bin/sardis-healthcheck
#!/usr/bin/env python3
"""Verify the Sardis SDK and core dependencies are importable."""
import sys

checks = {
    "sardis": "sardis",
    "httpx": "httpx",
    "sardis_e2b": "sardis_e2b",
}

failed = []
for name, module in checks.items():
    try:
        __import__(module)
    except ImportError:
        failed.append(name)

if failed:
    print(f"FAIL: could not import {', '.join(failed)}", file=sys.stderr)
    sys.exit(1)

print("OK: all Sardis sandbox dependencies available")
HEALTHCHECK

# Run healthcheck during build to catch packaging errors early
RUN python3 /usr/local/bin/sardis-healthcheck

# Pre-create a workspace directory
WORKDIR /home/user
