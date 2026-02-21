#!/usr/bin/env bash
# Sardis npm Publish Script
# Usage: ./scripts/publish-npm.sh [--dry-run]
#
# Prerequisites:
#   npm login (or set NPM_TOKEN)
#   Node.js >= 18

set -euo pipefail

DRY_RUN=false

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# npm packages in publish order
NPM_PACKAGES=(
  "sardis-sdk-js"
  "sardis-ai-sdk"
  "sardis-ramp-js"
  "sardis-mcp-server"
)

echo "========================================="
echo "  Sardis npm Publish"
echo "  Packages: ${#NPM_PACKAGES[@]}"
echo "  Dry Run: $DRY_RUN"
echo "========================================="

NPM_ARGS=""
if [ "$DRY_RUN" = true ]; then
  NPM_ARGS="--dry-run"
fi

SUCCESS=0
FAILED=0

for pkg in "${NPM_PACKAGES[@]}"; do
  PKG_DIR="$REPO_ROOT/packages/$pkg"

  if [ ! -f "$PKG_DIR/package.json" ]; then
    echo "SKIP: $pkg (no package.json)"
    continue
  fi

  NAME=$(node -e "console.log(require('$PKG_DIR/package.json').name)")
  VERSION=$(node -e "console.log(require('$PKG_DIR/package.json').version)")
  echo ""
  echo "--- $NAME@$VERSION ---"

  # Build if build script exists
  if node -e "const p=require('$PKG_DIR/package.json'); process.exit(p.scripts?.build ? 0 : 1)" 2>/dev/null; then
    echo "  Building..."
    if ! (cd "$PKG_DIR" && npm run build 2>&1 | tail -3); then
      echo "  FAILED: Build error for $NAME"
      FAILED=$((FAILED + 1))
      continue
    fi
  fi

  # Publish
  echo "  Publishing..."
  if (cd "$PKG_DIR" && npm publish --access public $NPM_ARGS 2>&1 | tail -3); then
    echo "  SUCCESS: $NAME@$VERSION published"
    SUCCESS=$((SUCCESS + 1))
  else
    echo "  FAILED: Publish error for $NAME"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "========================================="
echo "  Results: $SUCCESS success, $FAILED failed"
echo "========================================="
