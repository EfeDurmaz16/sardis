"""
Vercel serverless function entry point for Sardis API.

This file is the entry point for Vercel's Python runtime.
It imports and exposes the FastAPI app from apps/api.
"""
from __future__ import annotations

import os
import sys

# Add monorepo apps and packages to the path. The API app uses the dedicated
# `server` import package so it cannot collide with the public SDK.
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
apps_dir = os.path.join(root_dir, "apps")
packages_dir = os.path.join(root_dir, "packages")
sys.path[:0] = [
    os.path.join(apps_dir, "api"),
    os.path.join(packages_dir, "sardis-core", "src"),
    os.path.join(packages_dir, "sardis-wallet", "src"),
    os.path.join(packages_dir, "sardis-protocol", "src"),
    os.path.join(packages_dir, "sardis-chain", "src"),
    os.path.join(packages_dir, "sardis-ledger", "src"),
    os.path.join(packages_dir, "sardis-compliance", "src"),
    os.path.join(packages_dir, "sardis-cards", "src"),
]

from server.main import create_app  # noqa: E402

# Create the FastAPI app
app = create_app()

# Vercel expects the app to be named 'app' or 'handler'
handler = app
