"""
Vercel serverless function entry point for Sardis API.

This file is the entry point for Vercel's Python runtime.
It imports and exposes the FastAPI app from sardis-api.
"""
from __future__ import annotations

import os
import sys

# Add the sardis packages to the path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root_dir, "sardis-core", "src"))
sys.path.insert(0, os.path.join(root_dir, "sardis-api", "src"))
sys.path.insert(0, os.path.join(root_dir, "sardis-wallet", "src"))
sys.path.insert(0, os.path.join(root_dir, "sardis-protocol", "src"))
sys.path.insert(0, os.path.join(root_dir, "sardis-chain", "src"))
sys.path.insert(0, os.path.join(root_dir, "sardis-ledger", "src"))
sys.path.insert(0, os.path.join(root_dir, "sardis-compliance", "src"))

from sardis_api.main import create_app

# Create the FastAPI app
app = create_app()

# Vercel expects the app to be named 'app' or 'handler'
handler = app
