#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[clone-smoke] starting clone-and-run validation"

check_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[clone-smoke][fail] missing required command: $cmd"
    exit 1
  fi
}

check_cmd python3
check_cmd pnpm
check_cmd node
check_cmd pytest

if [[ "${1:-}" != "--no-install" ]]; then
  echo "[clone-smoke] installing Python dependencies"
  python3 -m pip install -r requirements.txt

  echo "[clone-smoke] installing Node workspace dependencies"
  pnpm install --no-frozen-lockfile
else
  echo "[clone-smoke] skipping dependency installation (--no-install)"
fi

echo "[clone-smoke] validating Python facade quick-start surface"
python3 - <<'PY'
from decimal import Decimal
from sardis import Agent, Policy

policy = Policy(max_per_tx=Decimal("100"))
agent = Agent(name="smoke-agent", policy=policy)
wallet = agent.create_wallet(initial_balance=Decimal("250"))
result = agent.pay(to="merchant:test", amount=Decimal("25"))

assert wallet.balance == Decimal("225")
assert result.success is True
print("[clone-smoke][pass] python facade smoke flow")
PY

echo "[clone-smoke] running readiness checks"
bash scripts/release/readiness_check.sh

echo "[clone-smoke] running critical-path checks"
bash scripts/release/critical_path_check.sh

echo "[clone-smoke] clone-and-run validation passed"
