from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCRIPT_PATH = Path("scripts/release/generate_provider_live_lane_artifact.py")


def _write_input(path: Path, *, base_score: int, critical_zero: bool = False) -> None:
    provider_scores = {
        "A1": base_score,
        "A2": base_score,
        "A3": base_score,
        "B1": base_score,
        "B2": base_score,
        "B3": base_score,
        "C1": base_score,
        "C2": base_score,
        "C3": base_score,
        "D1": base_score,
        "E1": base_score,
    }
    if critical_zero:
        provider_scores["A1"] = 0

    payload = {
        "pass_threshold": 23,
        "providers": {
            name: {"scores": dict(provider_scores), "notes": f"{name} notes"}
            for name in ("stripe", "lithic", "rain", "bridge")
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_provider_cert_generator_writes_artifacts(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    output_json = tmp_path / "out.json"
    output_dir = tmp_path / "sheets"
    _write_input(input_path, base_score=3)

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            "--input",
            str(input_path),
            "--output-json",
            str(output_json),
            "--output-dir",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert output_json.exists()

    artifact = json.loads(output_json.read_text(encoding="utf-8"))
    assert artifact["go_count"] == 4
    assert artifact["no_go_count"] == 0
    for provider in ("stripe", "lithic", "rain", "bridge"):
        assert (output_dir / f"{provider}-go-no-go-latest.md").exists()


def test_provider_cert_generator_strict_fails_on_no_go(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    output_json = tmp_path / "out.json"
    output_dir = tmp_path / "sheets"
    _write_input(input_path, base_score=1, critical_zero=True)

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            "--input",
            str(input_path),
            "--output-json",
            str(output_json),
            "--output-dir",
            str(output_dir),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "strict mode enabled and providers are not GO" in (result.stderr + result.stdout)

