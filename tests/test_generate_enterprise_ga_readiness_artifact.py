from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "release"
    / "generate_enterprise_ga_readiness_artifact.py"
)


def _write_common_inputs(root: Path, *, provider_no_go_count: int = 0) -> tuple[Path, Path, Path, Path]:
    ga_doc = root / "ga.md"
    ga_doc.write_text(
        "GA freeze policy\n/api/v2\nX-API-Version\n",
        encoding="utf-8",
    )

    provider = root / "provider.json"
    provider.write_text(
        json.dumps(
            {
                "providers": [{"provider": "stripe"}],
                "go_count": 1 if provider_no_go_count == 0 else 0,
                "no_go_count": provider_no_go_count,
            }
        ),
        encoding="utf-8",
    )

    ops = root / "ops.json"
    ops.write_text(
        json.dumps({"drill": {"checks": {"failover_rto_within_target": True, "rpo_within_target": True}}}),
        encoding="utf-8",
    )

    soc2 = root / "soc2.json"
    soc2.write_text(json.dumps({"evidence_count": 3}), encoding="utf-8")
    return ga_doc, provider, ops, soc2


def test_ga_artifact_generator_writes_output(tmp_path: Path) -> None:
    ga_doc, provider, ops, soc2 = _write_common_inputs(tmp_path, provider_no_go_count=0)
    output = tmp_path / "ga-artifact.json"

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            "--ga-doc",
            str(ga_doc),
            "--provider-cert",
            str(provider),
            "--ops-evidence",
            str(ops),
            "--soc2-manifest",
            str(soc2),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["overall_ready"] is True


def test_ga_artifact_generator_strict_fails_when_not_ready(tmp_path: Path) -> None:
    ga_doc, provider, ops, soc2 = _write_common_inputs(tmp_path, provider_no_go_count=1)
    output = tmp_path / "ga-artifact.json"

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            "--ga-doc",
            str(ga_doc),
            "--provider-cert",
            str(provider),
            "--ops-evidence",
            str(ops),
            "--soc2-manifest",
            str(soc2),
            "--output",
            str(output),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "strict mode enabled and readiness is false" in (result.stderr + result.stdout)

