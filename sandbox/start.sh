#!/bin/bash
# Sardis Sandbox Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🏖️  Starting Sardis Sandbox Environment"
echo "======================================="

# Create data directory
mkdir -p "$SCRIPT_DIR/data"

# Load sandbox environment
export $(cat "$SCRIPT_DIR/env.sandbox.template" | grep -v '^#' | xargs)

echo "✅ Environment loaded"
echo "   - SARDIS_ENVIRONMENT: $SARDIS_ENVIRONMENT"
echo "   - SARDIS_CHAIN_MODE: $SARDIS_CHAIN_MODE"
echo "   - DATABASE_URL: In-memory (sandbox mode)"

# Note: Sandbox uses in-memory repositories, no database seeding needed
echo "📦 Using in-memory storage (sandbox mode)"

# Start API server
echo ""
echo "🚀 Starting API server on http://localhost:8001"
echo "   - Health check: http://localhost:8001/health"
echo "   - API docs: http://localhost:8001/docs"
echo ""
echo "📝 Note: Sandbox uses in-memory storage. Data resets on restart."
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$PROJECT_ROOT"
uvicorn sardis_api.main:create_app --factory --host 0.0.0.0 --port 8001 --reload

