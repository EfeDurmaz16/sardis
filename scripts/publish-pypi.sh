#!/usr/bin/env bash
# Sardis PyPI Publish Script
# Usage: ./scripts/publish-pypi.sh [--dry-run] [--test-pypi]
#
# Prerequisites:
#   pip install build twine
#   Set TWINE_USERNAME and TWINE_PASSWORD (or use ~/.pypirc)
#   For TestPyPI: TWINE_REPOSITORY_URL=https://test.pypi.org/legacy/

set -euo pipefail

DRY_RUN=false
TEST_PYPI=false

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    --test-pypi) TEST_PYPI=true ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Python packages in publish order (dependencies first)
PYTHON_PACKAGES=(
  "sardis-core"
  "sardis-protocol"
  "sardis-chain"
  "sardis-wallet"
  "sardis-ledger"
  "sardis-compliance"
  "sardis-cards"
  "sardis-ramp"
  "sardis-checkout"
  "sardis-a2a"
  "sardis-ucp"
  "sardis-langchain"
  "sardis-crewai"
  "sardis-openai"
  "sardis-adk"
  "sardis-agent-sdk"
  "sardis-openclaw"
  "sardis-guardrails"
  "sardis-sdk-python"
  "sardis-cli"
  "sardis-api"
)

echo "========================================="
echo "  Sardis PyPI Publish"
echo "  Packages: ${#PYTHON_PACKAGES[@]}"
echo "  Dry Run: $DRY_RUN"
echo "  Test PyPI: $TEST_PYPI"
echo "========================================="

TWINE_ARGS=""
if [ "$TEST_PYPI" = true ]; then
  TWINE_ARGS="--repository testpypi"
fi

SUCCESS=0
FAILED=0
SKIPPED=0

for pkg in "${PYTHON_PACKAGES[@]}"; do
  PKG_DIR="$REPO_ROOT/packages/$pkg"

  if [ ! -f "$PKG_DIR/pyproject.toml" ]; then
    echo "SKIP: $pkg (no pyproject.toml)"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  VERSION=$(grep '^version' "$PKG_DIR/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')
  echo ""
  echo "--- $pkg v$VERSION ---"

  # Clean previous builds
  rm -rf "$PKG_DIR/dist" "$PKG_DIR/build" "$PKG_DIR"/*.egg-info

  # Build
  echo "  Building..."
  if ! (cd "$PKG_DIR" && python -m build --wheel --sdist 2>&1 | tail -3); then
    echo "  FAILED: Build error for $pkg"
    FAILED=$((FAILED + 1))
    continue
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "  DRY RUN: Would upload $(ls "$PKG_DIR"/dist/*.whl 2>/dev/null | head -1)"
    SUCCESS=$((SUCCESS + 1))
    continue
  fi

  # Upload
  echo "  Uploading to PyPI..."
  if twine upload $TWINE_ARGS "$PKG_DIR/dist/"* 2>&1 | tail -3; then
    echo "  SUCCESS: $pkg v$VERSION published"
    SUCCESS=$((SUCCESS + 1))
  else
    echo "  FAILED: Upload error for $pkg"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "========================================="
echo "  Results: $SUCCESS success, $FAILED failed, $SKIPPED skipped"
echo "========================================="
