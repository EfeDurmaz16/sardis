#!/usr/bin/env bash
# =============================================================================
# Sardis Database Migration Runner
# =============================================================================
#
# This is the SINGLE source of truth for applying database schema changes.
# It applies every non-rollback SQL file in apps/api/migrations/ in ordinal
# order, tracking applied versions in the schema_migrations table so re-runs
# are idempotent. It is the migration step for both the staging and production
# deploy pipelines (see .github/workflows/deploy.yml). Alembic has been retired.
#
# Usage:
#   ./scripts/run_migrations.sh                    # Apply all pending migrations
#   ./scripts/run_migrations.sh --dry-run          # Show which migrations would run
#   ./scripts/run_migrations.sh --mark-applied     # Record all current migrations
#                                                  #   as applied WITHOUT executing
#                                                  #   them (one-time Neon cutover;
#                                                  #   see docs/productization/
#                                                  #   MIGRATION_CUTOVER.md)
#   DATABASE_URL=postgres://... ./scripts/run_migrations.sh
#
# Idempotency:
#   Each migration is applied with ON_ERROR_STOP=1; on any SQL error the runner
#   aborts (non-zero exit) so a broken migration can never produce a false
#   "complete". On success the version is recorded in schema_migrations.
#   Already-recorded versions are skipped, so re-running against a migrated DB is
#   a no-op. Migration files own their own transaction boundaries (most are
#   wrapped IF NOT EXISTS / ADD COLUMN IF NOT EXISTS for safe re-apply; a few,
#   e.g. CREATE INDEX CONCURRENTLY, must run outside a transaction block, so the
#   runner does NOT force a wrapping transaction).
#
# =============================================================================
set -euo pipefail

MIGRATIONS_DIR="$(cd "$(dirname "$0")/../apps/api/migrations" && pwd)"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable is required"
    exit 1
fi

DRY_RUN=false
MARK_APPLIED=false
case "${1:-}" in
    --dry-run)      DRY_RUN=true ;;
    --mark-applied) MARK_APPLIED=true ;;
    "")             ;;
    *) echo "ERROR: unknown argument '$1' (expected --dry-run or --mark-applied)"; exit 1 ;;
esac

# psql invocation that fails the script on the first SQL error.
psql_strict() {
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 "$@"
}

echo "=== Sardis Migration Runner ==="
echo "Migrations dir: $MIGRATIONS_DIR"
if [ "$MARK_APPLIED" = true ]; then
    echo "Mode: --mark-applied (record versions WITHOUT executing migrations)"
elif [ "$DRY_RUN" = true ]; then
    echo "Mode: --dry-run (no changes)"
fi
echo ""

# Ensure schema_migrations table exists.
psql_strict -q -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
"

# Get applied migrations (version column may historically contain either a bare
# ordinal like '083' or a legacy 'NNN_name' value; we normalise to the leading
# ordinal when comparing so both forms are treated as applied).
APPLIED=$(psql_strict -t -A -c \
    "SELECT regexp_replace(version, '^([0-9]+).*', '\1') FROM schema_migrations;")

is_applied() {
    echo "$APPLIED" | grep -q "^${1}$"
}

# Apply (or mark) pending migrations in ordinal order.
for migration in "$MIGRATIONS_DIR"/[0-9]*.sql; do
    [ -f "$migration" ] || continue

    # Skip rollback files.
    [[ "$migration" == *_rollback.sql ]] && continue

    filename=$(basename "$migration")
    version=$(echo "$filename" | grep -oE '^[0-9]+')
    description=${filename#*_}
    description=${description%.sql}

    if is_applied "$version"; then
        echo "  [SKIP] $filename (already applied)"
        continue
    fi

    if [ "$DRY_RUN" = true ]; then
        echo "  [PENDING] $filename (would apply)"
        continue
    fi

    if [ "$MARK_APPLIED" = true ]; then
        echo "  [MARK]  $filename (recording as applied, NOT executing)"
        psql_strict -q -c \
            "INSERT INTO schema_migrations (version, description)
             VALUES ('${version}', '${description//\'/\'\'}')
             ON CONFLICT (version) DO NOTHING;"
        continue
    fi

    echo "  [APPLYING] $filename ..."
    # Apply the migration file. ON_ERROR_STOP=1 aborts the whole script (set -e)
    # on the first SQL error, so a broken migration is never silently skipped.
    # The file owns its own transaction boundaries; we do NOT force a wrapping
    # transaction because some migrations (CREATE INDEX CONCURRENTLY, etc.) must
    # run outside one.
    psql_strict -f "$migration"
    # Record the version only after a successful apply.
    psql_strict -q -c \
        "INSERT INTO schema_migrations (version, description)
         VALUES ('${version}', '${description//\'/\'\'}')
         ON CONFLICT (version) DO NOTHING;"
    echo "  [DONE] $filename"
done

echo ""
echo "=== Migration complete ==="
