"""
Vercel serverless function entry point for Sardis API.

This file is the entry point for Vercel's Python runtime.
It imports and exposes the FastAPI app from packages/server-api.
"""
from __future__ import annotations

import os
import sys

# Add monorepo packages to the path. The server API uses the dedicated
# `sardis_server` import package so it cannot collide with the public SDK.
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
packages_dir = os.path.join(root_dir, "packages")
sys.path[:0] = [
    os.path.join(packages_dir, "server-api", "src"),
    os.path.join(packages_dir, "sardis-core", "src"),
    os.path.join(packages_dir, "sardis-wallet", "src"),
    os.path.join(packages_dir, "sardis-protocol", "src"),
    os.path.join(packages_dir, "sardis-chain", "src"),
    os.path.join(packages_dir, "sardis-ledger", "src"),
    os.path.join(packages_dir, "sardis-compliance", "src"),
    os.path.join(packages_dir, "sardis-cards", "src"),
]

from sardis_server.main import create_app  # noqa: E402

# Create the FastAPI app
app = create_app()

# Vercel expects the app to be named 'app' or 'handler'
handler = app
