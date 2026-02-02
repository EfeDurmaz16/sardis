#!/usr/bin/env bash
# =============================================================================
# Sardis Database Migration Runner
# =============================================================================
#
# Usage:
#   ./scripts/run_migrations.sh                    # Apply all pending migrations
#   ./scripts/run_migrations.sh --dry-run          # Show which migrations would run
#   DATABASE_URL=postgres://... ./scripts/run_migrations.sh
#
# =============================================================================
set -euo pipefail

MIGRATIONS_DIR="$(cd "$(dirname "$0")/../packages/sardis-api/migrations" && pwd)"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable is required"
    exit 1
fi

DRY_RUN=false
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
fi

echo "=== Sardis Migration Runner ==="
echo "Migrations dir: $MIGRATIONS_DIR"
echo ""

# Ensure schema_migrations table exists
psql "$DATABASE_URL" -q -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(32) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
" 2>/dev/null

# Get applied migrations
APPLIED=$(psql "$DATABASE_URL" -t -A -c "SELECT version FROM schema_migrations ORDER BY version;")

# Find and apply pending migrations
for migration in "$MIGRATIONS_DIR"/[0-9]*.sql; do
    [ -f "$migration" ] || continue

    # Skip rollback files
    [[ "$migration" == *_rollback.sql ]] && continue

    filename=$(basename "$migration")
    version=$(echo "$filename" | grep -oE '^[0-9]+')

    if echo "$APPLIED" | grep -q "^${version}$"; then
        echo "  [SKIP] $filename (already applied)"
        continue
    fi

    if [ "$DRY_RUN" = true ]; then
        echo "  [PENDING] $filename (would apply)"
    else
        echo "  [APPLYING] $filename ..."
        psql "$DATABASE_URL" -f "$migration"
        echo "  [DONE] $filename"
    fi
done

echo ""
echo "=== Migration complete ==="
