"""Local development bootstrap helpers for the Sardis server package."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MONOREPO_SOURCE_PACKAGES = (
    "sardis-core",
    "sardis-wallet",
    "sardis-chain",
    "sardis-protocol",
    "sardis-ledger",
    "sardis-cards",
    "sardis-compliance",
    "sardis-checkout",
    "sardis-coinbase",
    "sardis-striga",
    "sardis-lightspark",
    "sardis-guardrails",
)


def bootstrap_monorepo_sys_path() -> None:
    """Make local monorepo packages importable without requiring PYTHONPATH.

    This is intentionally limited to local development and test environments.
    Installed/package deployments should resolve dependencies through normal
    package metadata instead of mutating ``sys.path``.
    """
    here = Path(__file__).resolve()
    repo_root: Path | None = None
    for parent in here.parents:
        if (parent / "packages").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        return

    packages_dir = repo_root / "packages"
    for package_name in MONOREPO_SOURCE_PACKAGES:
        src = packages_dir / package_name / "src"
        if src.is_dir():
            path = str(src)
            if path not in sys.path:
                sys.path.insert(0, path)


def should_bootstrap_monorepo_sys_path() -> bool:
    """Return whether local monorepo import bootstrapping is allowed."""
    disabled = os.getenv("SARDIS_DISABLE_MONOREPO_BOOTSTRAP", "").strip().lower()
    if disabled in {"1", "true", "yes", "on"}:
        return False

    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    return env in {"dev", "development", "sandbox", "staging", "test"}
