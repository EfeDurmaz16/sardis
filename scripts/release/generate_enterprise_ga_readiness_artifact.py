#!/usr/bin/env python3
"""Generate consolidated Enterprise GA readiness artifact."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"[ga-artifact][fail] missing json file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ga-artifact][fail] invalid json ({path}): {exc}") from exc


def _contains(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Enterprise GA readiness artifact")
    parser.add_argument(
        "--ga-doc",
        default="docs/design-partner/ga-prep-execution-pack-q1-2026.md",
        help="GA prep markdown path",
    )
    parser.add_argument(
        "--provider-cert",
        default="docs/audits/evidence/provider-live-lane-certification-latest.json",
        help="Provider certification artifact path",
    )
    parser.add_argument(
        "--ops-evidence",
        default="docs/audits/evidence/ops-readiness-latest.json",
        help="Ops readiness artifact path",
    )
    parser.add_argument(
        "--soc2-manifest",
        default="artifacts/compliance/soc2-evidence-manifest.json",
        help="SOC2 manifest artifact path",
    )
    parser.add_argument(
        "--output",
        default="docs/audits/evidence/enterprise-ga-readiness-latest.json",
        help="Output path",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if overall readiness=false")
    args = parser.parse_args()

    ga_doc_path = Path(args.ga_doc)
    if not ga_doc_path.exists():
        raise SystemExit(f"[ga-artifact][fail] missing GA prep doc: {ga_doc_path}")
    ga_doc = ga_doc_path.read_text(encoding="utf-8")

    provider = _load_json(Path(args.provider_cert))
    ops = _load_json(Path(args.ops_evidence))
    soc2 = _load_json(Path(args.soc2_manifest))

    api_freeze_checks = {
        "stable_v2_path_documented": _contains(ga_doc, r"/api/v2"),
        "version_header_documented": _contains(ga_doc, r"X-API-Version"),
        "freeze_policy_documented": _contains(ga_doc, r"freeze policy"),
    }

    provider_checks = {
        "artifact_present": True,
        "provider_count": len(provider.get("providers") or []),
        "go_count": int(provider.get("go_count") or 0),
        "no_go_count": int(provider.get("no_go_count") or 0),
        "all_providers_go": int(provider.get("no_go_count") or 0) == 0,
    }

    ops_checks = dict((ops.get("drill") or {}).get("checks") or {})
    ops_all_ok = bool(ops_checks) and all(bool(v) for v in ops_checks.values())

    soc2_checks = {
        "manifest_present": True,
        "evidence_count": int(soc2.get("evidence_count") or 0),
        "has_evidence_items": int(soc2.get("evidence_count") or 0) > 0,
    }

    readiness = {
        "api_freeze_ok": all(api_freeze_checks.values()),
        "provider_live_lane_ok": bool(provider_checks["all_providers_go"]),
        "ops_dr_ok": ops_all_ok,
        "soc2_manifest_ok": bool(soc2_checks["has_evidence_items"]),
    }
    overall_ready = all(readiness.values())

    artifact = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "overall_ready": overall_ready,
        "readiness": readiness,
        "api_freeze_checks": api_freeze_checks,
        "provider_checks": provider_checks,
        "ops_checks": ops_checks,
        "soc2_checks": soc2_checks,
        "sources": {
            "ga_doc": args.ga_doc,
            "provider_cert": args.provider_cert,
            "ops_evidence": args.ops_evidence,
            "soc2_manifest": args.soc2_manifest,
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[ga-artifact] wrote artifact: {output}")
    if not overall_ready:
        print("[ga-artifact] overall_ready=false")
        if args.strict:
            raise SystemExit("[ga-artifact][fail] strict mode enabled and readiness is false")
    print("[ga-artifact] pass")


if __name__ == "__main__":
    main()

