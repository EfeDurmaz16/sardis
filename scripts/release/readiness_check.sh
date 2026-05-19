#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[readiness] public OSS readiness gate"
echo "[readiness] private production, provider, compliance, and design-partner gates live outside this repository"

"$ROOT_DIR/scripts/check_release_readiness.sh"
