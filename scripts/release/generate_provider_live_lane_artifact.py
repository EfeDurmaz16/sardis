#!/usr/bin/env python3
"""Generate provider live-lane certification artifacts.

Reads a provider score input JSON and emits:
1) machine-readable certification JSON artifact
2) per-provider GO/NO-GO markdown sheets
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List


CRITICAL_KEYS: List[str] = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]
ALL_KEYS: List[str] = CRITICAL_KEYS + ["D1", "E1"]
DEFAULT_PROVIDERS: List[str] = ["stripe", "lithic", "rain", "bridge"]


def _load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"[provider-cert][fail] missing input file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[provider-cert][fail] invalid JSON input ({path}): {exc}") from exc


def _validate_scores(provider: str, scores: Dict[str, Any]) -> Dict[str, int]:
    normalized: Dict[str, int] = {}
    for key in ALL_KEYS:
        if key not in scores:
            raise SystemExit(f"[provider-cert][fail] provider={provider} missing score key: {key}")
        value = scores[key]
        if not isinstance(value, int) or value < 0 or value > 3:
            raise SystemExit(
                f"[provider-cert][fail] provider={provider} score {key} must be integer in range 0..3, got: {value!r}"
            )
        normalized[key] = value
    return normalized


def _decision(scores: Dict[str, int], threshold: int) -> str:
    has_critical_zero = any(scores[key] == 0 for key in CRITICAL_KEYS)
    total = sum(scores.values())
    if has_critical_zero:
        return "NO_GO_CRITICAL_ZERO"
    if total >= threshold:
        return "GO"
    return "NO_GO_SCORE"


def _build_provider_result(provider: str, scores: Dict[str, int], threshold: int, notes: str) -> Dict[str, Any]:
    total = sum(scores.values())
    decision = _decision(scores, threshold)
    critical_zero_keys = [k for k in CRITICAL_KEYS if scores[k] == 0]
    return {
        "provider": provider,
        "scores": scores,
        "total": total,
        "threshold": threshold,
        "decision": decision,
        "critical_zero_keys": critical_zero_keys,
        "notes": notes,
    }


def _write_provider_markdown(path: Path, result: Dict[str, Any]) -> None:
    provider = result["provider"]
    decision = result["decision"]
    total = result["total"]
    threshold = result["threshold"]
    notes = result.get("notes", "")
    critical_zero_keys = result.get("critical_zero_keys", [])
    scores = result["scores"]

    lines = [
        f"# {provider.title()} Live-Lane GO/NO-GO",
        "",
        f"- Decision: **{decision}**",
        f"- Score: **{total}/{len(ALL_KEYS) * 3}**",
        f"- Pass Threshold: **{threshold}**",
        "",
        "## Scores",
        "",
        "| Key | Score |",
        "| --- | ---: |",
    ]
    for key in ALL_KEYS:
        lines.append(f"| {key} | {scores[key]} |")

    lines.extend(
        [
            "",
            "## Critical Zero Keys",
            "",
            ", ".join(critical_zero_keys) if critical_zero_keys else "None",
            "",
            "## Notes",
            "",
            notes or "_No notes provided_",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate provider live-lane certification artifacts")
    parser.add_argument(
        "--input",
        default="docs/design-partner/provider-live-lane-certification-input.json",
        help="Input score JSON",
    )
    parser.add_argument(
        "--output-json",
        default="docs/audits/evidence/provider-live-lane-certification-latest.json",
        help="Output artifact JSON path",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/audits/evidence/provider-go-no-go",
        help="Output directory for per-provider markdown sheets",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any provider is not GO",
    )
    parser.add_argument(
        "--providers",
        nargs="*",
        default=DEFAULT_PROVIDERS,
        help="Providers to evaluate (default: stripe lithic rain bridge)",
    )
    args = parser.parse_args()

    payload = _load(Path(args.input))
    threshold = int(payload.get("pass_threshold", 23))
    providers_blob = payload.get("providers") or {}
    if not isinstance(providers_blob, dict):
        raise SystemExit("[provider-cert][fail] providers must be a JSON object")

    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    results: List[Dict[str, Any]] = []
    for provider in args.providers:
        provider_key = provider.strip().lower()
        raw_provider = providers_blob.get(provider_key)
        if not isinstance(raw_provider, dict):
            raise SystemExit(f"[provider-cert][fail] missing provider entry in input: {provider_key}")
        raw_scores = raw_provider.get("scores", {})
        if not isinstance(raw_scores, dict):
            raise SystemExit(f"[provider-cert][fail] provider={provider_key} scores must be object")
        notes = str(raw_provider.get("notes", "")).strip()
        scores = _validate_scores(provider_key, raw_scores)
        result = _build_provider_result(provider_key, scores, threshold, notes)
        results.append(result)

    summary = {
        "generated_at": generated_at,
        "input": args.input,
        "threshold": threshold,
        "providers": results,
        "go_count": sum(1 for r in results if r["decision"] == "GO"),
        "no_go_count": sum(1 for r in results if r["decision"] != "GO"),
    }

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    output_dir = Path(args.output_dir)
    for result in results:
        md_path = output_dir / f"{result['provider']}-go-no-go-latest.md"
        _write_provider_markdown(md_path, result)

    print(f"[provider-cert] wrote JSON artifact: {output_json}")
    print(f"[provider-cert] wrote provider sheets: {output_dir}")

    if args.strict:
        not_go = [r["provider"] for r in results if r["decision"] != "GO"]
        if not_go:
            raise SystemExit(
                "[provider-cert][fail] strict mode enabled and providers are not GO: " + ", ".join(sorted(not_go))
            )
    print("[provider-cert] pass")


if __name__ == "__main__":
    main()

