#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[deps] starting dependency vulnerability audit"

if ! command -v pip-audit >/dev/null 2>&1; then
  echo "[deps][fail] pip-audit not installed"
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "[deps][fail] pnpm not installed"
  exit 1
fi

echo "[deps] running pip-audit against pyproject.toml"
pip-audit

echo "[deps] installing node dependencies for audit graph"
pnpm install --frozen-lockfile

echo "[deps] running pnpm audit (severity >= high, prod deps)"
pnpm audit --audit-level high --prod

echo "[deps] dependency audit completed successfully"
