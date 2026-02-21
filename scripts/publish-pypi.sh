#!/usr/bin/env bash
# Sardis PyPI Publish Script
# Usage: ./scripts/publish-pypi.sh [OPTIONS] [package-name]
#
# Options:
#   --dry-run     Perform a dry run without publishing
#   --test-pypi   Publish to TestPyPI instead
#   --list        List all publishable packages
#   --help        Show this help message
#
# Examples:
#   ./scripts/publish-pypi.sh sardis-core
#   ./scripts/publish-pypi.sh --dry-run sardis-sdk-python
#   ./scripts/publish-pypi.sh --list
#
# Prerequisites:
#   uv installed (or pip install build twine)
#   Set TWINE_USERNAME and TWINE_PASSWORD (or use ~/.pypirc)

set -euo pipefail

DRY_RUN=false
TEST_PYPI=false
PACKAGE_NAME=""

print_usage() {
  echo "Usage: $0 [OPTIONS] [package-name]"
  echo ""
  echo "Options:"
  echo "  --dry-run     Perform a dry run without publishing"
  echo "  --test-pypi   Publish to TestPyPI instead"
  echo "  --list        List all publishable packages"
  echo "  --help        Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 sardis-core"
  echo "  $0 --dry-run sardis-sdk-python"
  echo "  $0 --list"
}

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

list_packages() {
  echo "Publishable Python packages (in dependency order):"
  for pkg in "${PYTHON_PACKAGES[@]}"; do
    if [ -f "$REPO_ROOT/packages/$pkg/pyproject.toml" ]; then
      VERSION=$(grep '^version' "$REPO_ROOT/packages/$pkg/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')
      echo "  - $pkg (v$VERSION)"
    fi
  done
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --test-pypi) TEST_PYPI=true; shift ;;
    --list) list_packages; exit 0 ;;
    --help) print_usage; exit 0 ;;
    -*) echo "Unknown option: $1"; print_usage; exit 1 ;;
    *) PACKAGE_NAME="$1"; shift ;;
  esac
done

# If no package specified, publish all
if [ -z "$PACKAGE_NAME" ]; then
  PACKAGES_TO_PUBLISH=("${PYTHON_PACKAGES[@]}")
else
  # Validate package name
  VALID=false
  for pkg in "${PYTHON_PACKAGES[@]}"; do
    if [ "$pkg" = "$PACKAGE_NAME" ]; then
      VALID=true
      break
    fi
  done

  if [ "$VALID" = false ]; then
    echo "Error: Invalid package name: $PACKAGE_NAME"
    echo ""
    list_packages
    exit 1
  fi

  PACKAGES_TO_PUBLISH=("$PACKAGE_NAME")
fi

echo "========================================="
echo "  Sardis PyPI Publish"
echo "  Packages: ${#PACKAGES_TO_PUBLISH[@]}"
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

for pkg in "${PACKAGES_TO_PUBLISH[@]}"; do
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

  # Build with uv (fallback to python -m build)
  echo "  Building..."
  if command -v uv &> /dev/null; then
    if ! (cd "$PKG_DIR" && uv build 2>&1 | tail -3); then
      echo "  FAILED: Build error for $pkg"
      FAILED=$((FAILED + 1))
      continue
    fi
  else
    if ! (cd "$PKG_DIR" && python -m build --wheel --sdist 2>&1 | tail -3); then
      echo "  FAILED: Build error for $pkg"
      FAILED=$((FAILED + 1))
      continue
    fi
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "  DRY RUN: Would upload $(ls "$PKG_DIR"/dist/*.whl 2>/dev/null | head -1)"
    SUCCESS=$((SUCCESS + 1))
    continue
  fi

  # Upload with uv (fallback to twine)
  echo "  Uploading to PyPI..."
  if command -v uv &> /dev/null; then
    if (cd "$PKG_DIR" && uv publish $TWINE_ARGS 2>&1 | tail -3); then
      echo "  SUCCESS: $pkg v$VERSION published"
      SUCCESS=$((SUCCESS + 1))
    else
      echo "  FAILED: Upload error for $pkg"
      FAILED=$((FAILED + 1))
    fi
  else
    if twine upload $TWINE_ARGS "$PKG_DIR/dist/"* 2>&1 | tail -3; then
      echo "  SUCCESS: $pkg v$VERSION published"
      SUCCESS=$((SUCCESS + 1))
    else
      echo "  FAILED: Upload error for $pkg"
      FAILED=$((FAILED + 1))
    fi
  fi
done

echo ""
echo "========================================="
echo "  Results: $SUCCESS success, $FAILED failed, $SKIPPED skipped"
echo "========================================="

if [ $FAILED -gt 0 ]; then
  exit 1
fi
