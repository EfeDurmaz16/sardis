#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[metadata] validating package metadata and license coverage"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[metadata][fail] python3 is required"
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[metadata][fail] node is required"
  exit 1
fi

python3 - <<'PY'
import glob
import pathlib
import sys
import tomllib

failures = []
required_project = ["name", "version", "description", "license", "requires-python"]

for pyproject in sorted(glob.glob("packages/*/pyproject.toml")):
    data = tomllib.loads(pathlib.Path(pyproject).read_text(encoding="utf-8"))
    project = data.get("project", {})
    missing = [k for k in required_project if not project.get(k)]
    urls = project.get("urls", {})
    for key in ("Homepage", "Repository"):
        if not urls.get(key):
            missing.append(f"urls.{key}")
    if missing:
        failures.append(f"{pyproject}: missing {', '.join(missing)}")

if failures:
    for line in failures:
        print(f"[metadata][fail] {line}")
    sys.exit(1)
print("[metadata][pass] pyproject metadata is complete")
PY

for package_json in packages/*/package.json; do
  node -e '
    const fs = require("fs");
    const pkgPath = process.argv[1];
    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
    const missing = [];
    for (const key of ["name", "version", "description", "license", "main", "types", "exports"]) {
      if (!pkg[key]) missing.push(key);
    }
    if (!pkg.repository || !pkg.repository.url) missing.push("repository.url");
    if (!pkg.homepage) missing.push("homepage");
    if (missing.length) {
      console.log(`[metadata][fail] ${pkgPath}: missing ${missing.join(", ")}`);
      process.exit(1);
    }
  ' "$package_json"
done
echo "[metadata][pass] package.json metadata is complete"

license_failures=0
for pkg_dir in packages/*; do
  if [[ -f "$pkg_dir/pyproject.toml" || -f "$pkg_dir/package.json" ]]; then
    if [[ ! -f "$pkg_dir/LICENSE" ]]; then
      echo "[metadata][fail] missing LICENSE in $pkg_dir"
      license_failures=$((license_failures + 1))
    fi
  fi
done

if [[ "$license_failures" -gt 0 ]]; then
  exit 1
fi

echo "[metadata][pass] license files present for all publishable packages"
echo "[metadata] all metadata checks passed"
