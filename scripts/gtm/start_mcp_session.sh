#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found. Install Codex CLI first."
  exit 1
fi

cd "${ROOT_DIR}"
echo "Starting Codex interactive session in: ${ROOT_DIR}"
echo "Tip: verify MCPs with: codex mcp list"
echo "Tip: if needed, run: codex mcp login attio"
exec codex
