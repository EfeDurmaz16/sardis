#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DO_INSTALL=0
DO_VERIFY=0

usage() {
  cat <<'EOF'
Usage:
  bash ./scripts/bootstrap_js_env.sh [--install] [--verify]

Options:
  --install   Run pnpm install --no-frozen-lockfile after preflight checks.
  --verify    Run JS package test/build verification after checks (and install if requested).

Notes:
  - Without --install, this script only performs environment and network preflight checks.
  - Use this before running strict release readiness checks.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --install) DO_INSTALL=1 ;;
    --verify) DO_VERIFY=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "[bootstrap-js] Unknown argument: $arg"
      usage
      exit 1
      ;;
  esac
done

echo "[bootstrap-js] Root: $ROOT_DIR"

if ! command -v node >/dev/null 2>&1; then
  echo "[bootstrap-js] ERROR: node is not installed or not in PATH."
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "[bootstrap-js] ERROR: pnpm is not installed or not in PATH."
  exit 1
fi

NODE_VERSION="$(node -v)"
PNPM_VERSION="$(pnpm -v)"
PACKAGE_MANAGER="$(node -p "require('./package.json').packageManager" 2>/dev/null || true)"

echo "[bootstrap-js] node: $NODE_VERSION"
echo "[bootstrap-js] pnpm: $PNPM_VERSION"
if [[ -n "$PACKAGE_MANAGER" ]]; then
  echo "[bootstrap-js] packageManager: $PACKAGE_MANAGER"
fi

if ! node -e "require('dns').promises.lookup('registry.npmjs.org').then(()=>process.exit(0)).catch(()=>process.exit(1))"; then
  echo "[bootstrap-js] ERROR: Cannot resolve registry.npmjs.org from this environment."
  echo "[bootstrap-js] Hint: fix DNS/network, then retry with --install."
  exit 1
fi
echo "[bootstrap-js] DNS check passed: registry.npmjs.org"

if ! node -e "require('https').get('https://registry.npmjs.org/-/ping', (res) => process.exit(res.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"; then
  echo "[bootstrap-js] ERROR: Cannot reach npm registry ping endpoint."
  echo "[bootstrap-js] Hint: check firewall/proxy/VPN and npm registry configuration."
  exit 1
fi
echo "[bootstrap-js] Registry reachability check passed"

if [[ "$DO_INSTALL" == "1" ]]; then
  echo "[bootstrap-js] Installing dependencies..."
  (
    cd "$ROOT_DIR"
    pnpm install --no-frozen-lockfile
  )
fi

if [[ "$DO_VERIFY" == "1" ]]; then
  echo "[bootstrap-js] Running JS verification gates..."
  (
    cd "$ROOT_DIR"
    pnpm run test:mcp
    pnpm run build:mcp
    pnpm run test:ts-sdks
    pnpm run build:ts-sdks
  )
fi

echo "[bootstrap-js] Completed successfully."
