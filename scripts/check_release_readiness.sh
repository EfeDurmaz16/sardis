#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRICT_MODE="${STRICT_MODE:-0}"

echo "[release-readiness] Starting checks (STRICT_MODE=${STRICT_MODE})"

node_checks_skipped=0
have_vitest=0
if [[ -x "$ROOT_DIR/node_modules/.bin/vitest" || -x "$ROOT_DIR/packages/sardis-mcp-server/node_modules/.bin/vitest" ]]; then
  have_vitest=1
fi

if command -v pnpm >/dev/null 2>&1 && [[ -d "$ROOT_DIR/node_modules" ]] && [[ "$have_vitest" == "1" ]]; then
  echo "[release-readiness] Running Node package checks"
  (
    cd "$ROOT_DIR"
    pnpm run test:mcp
    pnpm run build:mcp
    pnpm run test:ts-sdks
    pnpm run build:ts-sdks
  )
else
  node_checks_skipped=1
  echo "[release-readiness] Skipping Node checks (pnpm/node_modules/vitest missing)"
  echo "  To enable:"
  echo "    pnpm run bootstrap:js:install"
  echo "  or manual:"
  echo "    pnpm install --no-frozen-lockfile"
fi

if [[ "$STRICT_MODE" == "1" && "$node_checks_skipped" == "1" ]]; then
  echo "[release-readiness] STRICT_MODE=1 requires Node checks; failing due to skipped checks"
  exit 1
fi

echo "[release-readiness] Running Python SDK + protocol checks"
"$ROOT_DIR/scripts/check_python_release_readiness.sh"

echo "[release-readiness] Completed"
