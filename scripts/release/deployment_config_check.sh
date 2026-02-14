#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[deploy] validating Vercel and deployment workflow consistency"

failures=0

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[deploy][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_match '"framework": "vite"' vercel.json "root vercel config must target Vite"
require_match '"buildCommand": "cd landing && npm run build"' vercel.json "root vercel build command must target landing"
require_match '"outputDirectory": "landing/dist"' vercel.json "root vercel output directory must target landing/dist"
require_match '"routes"' landing/vercel.json "landing vercel config must include SPA routes"

require_match 'build-landing:' .github/workflows/ci.yml "CI must include landing build job"
require_match 'working-directory: landing' .github/workflows/ci.yml "CI landing build must run in landing directory"

require_match 'deploy-landing-staging:' .github/workflows/deploy.yml "deploy workflow missing landing staging job"
require_match 'deploy-landing-production:' .github/workflows/deploy.yml "deploy workflow missing landing production job"
require_match 'VITE_API_URL: https://api-staging.sardis.sh' .github/workflows/deploy.yml "staging landing deploy must use staging API URL"
require_match 'VITE_API_URL: https://api.sardis.sh' .github/workflows/deploy.yml "prod landing deploy must use prod API URL"
require_match 'deploy-api-staging:' .github/workflows/deploy.yml "deploy workflow missing API staging job"
require_match 'deploy-api-production:' .github/workflows/deploy.yml "deploy workflow missing API production job"
require_match 'alembic upgrade head' .github/workflows/deploy.yml "API deploy must run alembic migrations"
require_match 'Release gate - webhook conformance' .github/workflows/deploy.yml "deploy workflow must include webhook conformance release gate"
require_match 'webhook_conformance_check.sh' .github/workflows/deploy.yml "deploy workflow must run webhook conformance script"

if [[ "$failures" -gt 0 ]]; then
  echo "[deploy] completed with $failures failure(s)"
  exit 1
fi

echo "[deploy] deployment configuration checks passed"
