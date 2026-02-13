#!/usr/bin/env bash
set -euo pipefail

# Sardis pre-launch readiness check scaffold.
# This script is intentionally minimal and expanded in later tasks.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[readiness] starting scaffold checks"

if ! command -v git >/dev/null 2>&1; then
  echo "[readiness] error: git is required"
  exit 1
fi

if ! command -v rg >/dev/null 2>&1; then
  echo "[readiness] warning: rg not found (fallback checks needed later)"
fi

echo "[readiness] TODO: verify README quick-start parity against SDK APIs"
echo "[readiness] TODO: verify MCP tool count from runtime source-of-truth"
echo "[readiness] TODO: verify package version consistency"
echo "[readiness] TODO: run smoke tests for examples and startup"
echo "[readiness] TODO: run security dependency audit"

echo "[readiness] scaffold complete"
