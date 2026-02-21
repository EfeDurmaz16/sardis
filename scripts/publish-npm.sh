#!/usr/bin/env bash
# Sardis npm Publish Script
# Usage: ./scripts/publish-npm.sh [OPTIONS] [package-name]
#
# Options:
#   --dry-run     Perform a dry run without publishing
#   --list        List all publishable packages
#   --help        Show this help message
#
# Examples:
#   ./scripts/publish-npm.sh sardis-sdk-js
#   ./scripts/publish-npm.sh --dry-run sardis-mcp-server
#   ./scripts/publish-npm.sh --list
#
# Prerequisites:
#   npm login (or set NPM_TOKEN)
#   Node.js >= 18
#   pnpm installed

set -euo pipefail

DRY_RUN=false
PACKAGE_NAME=""

print_usage() {
  echo "Usage: $0 [OPTIONS] [package-name]"
  echo ""
  echo "Options:"
  echo "  --dry-run     Perform a dry run without publishing"
  echo "  --list        List all publishable packages"
  echo "  --help        Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 sardis-sdk-js"
  echo "  $0 --dry-run sardis-mcp-server"
  echo "  $0 --list"
}

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# npm packages in publish order (dependencies first)
NPM_PACKAGES=(
  "sardis-sdk-js"
  "sardis-ai-sdk"
  "sardis-ramp-js"
  "sardis-mcp-server"
)

list_packages() {
  echo "Publishable npm packages (in dependency order):"
  for pkg in "${NPM_PACKAGES[@]}"; do
    if [ -f "$REPO_ROOT/packages/$pkg/package.json" ]; then
      NAME=$(node -e "console.log(require('$REPO_ROOT/packages/$pkg/package.json').name)")
      VERSION=$(node -e "console.log(require('$REPO_ROOT/packages/$pkg/package.json').version)")
      echo "  - $pkg ($NAME@$VERSION)"
    fi
  done
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --list) list_packages; exit 0 ;;
    --help) print_usage; exit 0 ;;
    -*) echo "Unknown option: $1"; print_usage; exit 1 ;;
    *) PACKAGE_NAME="$1"; shift ;;
  esac
done

# If no package specified, publish all
if [ -z "$PACKAGE_NAME" ]; then
  PACKAGES_TO_PUBLISH=("${NPM_PACKAGES[@]}")
else
  # Validate package name
  VALID=false
  for pkg in "${NPM_PACKAGES[@]}"; do
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
echo "  Sardis npm Publish"
echo "  Packages: ${#PACKAGES_TO_PUBLISH[@]}"
echo "  Dry Run: $DRY_RUN"
echo "========================================="

NPM_ARGS=""
if [ "$DRY_RUN" = true ]; then
  NPM_ARGS="--dry-run"
fi

SUCCESS=0
FAILED=0
SKIPPED=0

for pkg in "${PACKAGES_TO_PUBLISH[@]}"; do
  PKG_DIR="$REPO_ROOT/packages/$pkg"

  if [ ! -f "$PKG_DIR/package.json" ]; then
    echo "SKIP: $pkg (no package.json)"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  NAME=$(node -e "console.log(require('$PKG_DIR/package.json').name)")
  VERSION=$(node -e "console.log(require('$PKG_DIR/package.json').version)")
  echo ""
  echo "--- $NAME@$VERSION ---"

  # Build if build script exists
  if node -e "const p=require('$PKG_DIR/package.json'); process.exit(p.scripts?.build ? 0 : 1)" 2>/dev/null; then
    echo "  Building..."
    # Use pnpm if available, fallback to npm
    if command -v pnpm &> /dev/null; then
      if ! (cd "$PKG_DIR" && pnpm build 2>&1 | tail -3); then
        echo "  FAILED: Build error for $NAME"
        FAILED=$((FAILED + 1))
        continue
      fi
    else
      if ! (cd "$PKG_DIR" && npm run build 2>&1 | tail -3); then
        echo "  FAILED: Build error for $NAME"
        FAILED=$((FAILED + 1))
        continue
      fi
    fi
  fi

  # Publish
  echo "  Publishing..."
  # Use pnpm if available, fallback to npm
  if command -v pnpm &> /dev/null; then
    if (cd "$PKG_DIR" && pnpm publish --access public --no-git-checks $NPM_ARGS 2>&1 | tail -3); then
      echo "  SUCCESS: $NAME@$VERSION published"
      SUCCESS=$((SUCCESS + 1))
    else
      echo "  FAILED: Publish error for $NAME"
      FAILED=$((FAILED + 1))
    fi
  else
    if (cd "$PKG_DIR" && npm publish --access public $NPM_ARGS 2>&1 | tail -3); then
      echo "  SUCCESS: $NAME@$VERSION published"
      SUCCESS=$((SUCCESS + 1))
    else
      echo "  FAILED: Publish error for $NAME"
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
