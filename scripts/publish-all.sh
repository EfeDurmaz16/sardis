#!/usr/bin/env bash
# Sardis Publish All Packages
# Usage: ./scripts/publish-all.sh [OPTIONS]
#
# Options:
#   --dry-run     Perform a dry run without publishing
#   --test-pypi   Publish Python packages to TestPyPI
#   --python-only Publish only Python packages
#   --npm-only    Publish only npm packages
#   --help        Show this help message
#
# Examples:
#   ./scripts/publish-all.sh
#   ./scripts/publish-all.sh --dry-run
#   ./scripts/publish-all.sh --python-only
#
# This script publishes all packages in the correct dependency order:
#   1. Python packages (sardis-core → sardis-api → sardis-sdk-python → sardis-cli)
#   2. npm packages (sardis-sdk-js → sardis-mcp-server)

set -euo pipefail

DRY_RUN=false
TEST_PYPI=false
PYTHON_ONLY=false
NPM_ONLY=false

print_usage() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --dry-run     Perform a dry run without publishing"
  echo "  --test-pypi   Publish Python packages to TestPyPI"
  echo "  --python-only Publish only Python packages"
  echo "  --npm-only    Publish only npm packages"
  echo "  --help        Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0"
  echo "  $0 --dry-run"
  echo "  $0 --python-only"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --test-pypi) TEST_PYPI=true; shift ;;
    --python-only) PYTHON_ONLY=true; shift ;;
    --npm-only) NPM_ONLY=true; shift ;;
    --help) print_usage; exit 0 ;;
    -*) echo "Unknown option: $1"; print_usage; exit 1 ;;
    *) echo "Unknown argument: $1"; print_usage; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "  Sardis Publish All Packages"
echo "  Dry Run: $DRY_RUN"
echo "  Test PyPI: $TEST_PYPI"
echo "  Python Only: $PYTHON_ONLY"
echo "  npm Only: $NPM_ONLY"
echo "========================================="
echo ""

PYTHON_FAILED=false
NPM_FAILED=false

# Publish Python packages
if [ "$NPM_ONLY" = false ]; then
  echo "========================================="
  echo "  Step 1: Publishing Python Packages"
  echo "========================================="
  echo ""

  PYTHON_ARGS=""
  if [ "$DRY_RUN" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --dry-run"
  fi
  if [ "$TEST_PYPI" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --test-pypi"
  fi

  if ! bash "$SCRIPT_DIR/publish-pypi.sh" $PYTHON_ARGS; then
    echo ""
    echo "WARNING: Python package publishing failed"
    PYTHON_FAILED=true
  fi

  echo ""
  echo "Python packages published."
  echo ""
fi

# Publish npm packages
if [ "$PYTHON_ONLY" = false ]; then
  echo "========================================="
  echo "  Step 2: Publishing npm Packages"
  echo "========================================="
  echo ""

  NPM_ARGS=""
  if [ "$DRY_RUN" = true ]; then
    NPM_ARGS="$NPM_ARGS --dry-run"
  fi

  if ! bash "$SCRIPT_DIR/publish-npm.sh" $NPM_ARGS; then
    echo ""
    echo "WARNING: npm package publishing failed"
    NPM_FAILED=true
  fi

  echo ""
  echo "npm packages published."
  echo ""
fi

# Final summary
echo "========================================="
echo "  Publish All Complete"
echo "========================================="

if [ "$PYTHON_FAILED" = true ] || [ "$NPM_FAILED" = true ]; then
  echo ""
  echo "Some packages failed to publish:"
  if [ "$PYTHON_FAILED" = true ]; then
    echo "  - Python packages: FAILED"
  fi
  if [ "$NPM_FAILED" = true ]; then
    echo "  - npm packages: FAILED"
  fi
  echo ""
  echo "Check the output above for details."
  exit 1
else
  echo ""
  echo "All packages published successfully!"
  echo ""
fi
