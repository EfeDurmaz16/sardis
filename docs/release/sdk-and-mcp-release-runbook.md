# Sardis MCP + SDK Start-to-End Release Flow

This runbook defines the canonical release flow for:

- `@sardis/mcp-server`
- `@sardis/sdk`
- `@sardis/ai-sdk`
- `sardis-sdk` (PyPI)

## 1) Preconditions

1. CI is green on target commit.
2. Package versions are updated:
   - TypeScript packages: `package.json` `version`.
   - Python SDK: `pyproject.toml` and `src/sardis_sdk/__init__.py`.
3. Changelogs updated.
4. Required secrets are configured in GitHub:
   - `NPM_TOKEN`
   - `TEST_PYPI_API_TOKEN`
   - `PYPI_API_TOKEN`

## 2) Local Readiness Checks

From repo root:

```bash
pnpm run bootstrap:js:install
pnpm run check:release-readiness:strict
```

`check:release-readiness:strict` fails immediately if Node package gates cannot run.
`bootstrap:js:install` performs DNS and npm registry preflight checks before install.

Python package build check:

```bash
cd packages/sardis-sdk-python
python3 -m build
python3 -m twine check dist/*
```

If local network blocks npm/PyPI access, run Python-only readiness checks locally and rely on CI for Node package validation:

```bash
pnpm run bootstrap:js
pnpm run check:release-readiness
```

Live-chain conformance (Turnkey + testnet RPC) can be run separately:

```bash
pnpm run check:live-chain
```

Use strict mode in release environments to fail if live-chain credentials are not provided:

```bash
pnpm run check:live-chain:strict
```

## 3) Prerelease (Recommended First)

Prerelease publishes to:

- npm with tag `next`
- TestPyPI for Python

### Tag format

- MCP: `mcp-vX.Y.Z-rc.N`
- TS SDK: `sdk-js-vX.Y.Z-rc.N`
- AI SDK: `ai-sdk-vX.Y.Z-rc.N`
- Python SDK: `py-sdk-vX.Y.ZrcN` (PEP 440 style) or aligned project convention

### Trigger

Push tag:

```bash
git tag mcp-v0.1.1-rc.1
git push origin mcp-v0.1.1-rc.1
```

Equivalent for other packages.

Or run manual workflow dispatch:

- `Release NPM Packages`
- `Release Python SDK`

## 4) Stable Release

Stable publishes to:

- npm with tag `latest`
- PyPI

### Tag format

- MCP: `mcp-vX.Y.Z`
- TS SDK: `sdk-js-vX.Y.Z`
- AI SDK: `ai-sdk-vX.Y.Z`
- Python SDK: `py-sdk-vX.Y.Z`

### Trigger

Push stable tags:

```bash
git tag sdk-js-v0.2.1
git push origin sdk-js-v0.2.1
```

## 5) Post-publish Smoke Validation

### npm

```bash
npm view @sardis/mcp-server version
npm view @sardis/sdk version
npm view @sardis/ai-sdk version
npx -y @sardis/mcp-server@<version> --help
node -e "import('@sardis/sdk').then(()=>console.log('ok'))"
node -e "import('@sardis/ai-sdk').then(()=>console.log('ok'))"
```

### Python

```bash
python3 -m venv /tmp/sardis-smoke
source /tmp/sardis-smoke/bin/activate
pip install --upgrade pip
pip install sardis-sdk==<version>
python -c "import sardis_sdk; print(sardis_sdk.__version__)"
```

## 6) Rollback / Recovery

1. If prerelease fails, fix and republish with next prerelease increment.
2. Avoid deleting published versions.
3. For npm stable issues:
   - publish patched version `X.Y.Z+1`
   - optionally switch dist-tag from `latest` to previous safe version.
4. For PyPI stable issues:
   - publish patched version (PyPI versions are immutable).

## 7) CI Workflows Used

- `.github/workflows/ci.yml`
- `.github/workflows/release-npm.yml`
- `.github/workflows/release-python-sdk.yml`
- `docs/release/design-partner-staging-readiness.md`
- `docs/release/start-to-end-engineering-flow.md`
