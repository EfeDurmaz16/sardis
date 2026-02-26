from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "release"
    / "generate_ops_readiness_evidence.py"
)


def _write_runbooks(root: Path) -> None:
    files = [
        root / "ops-slo-alerts-rollback-runbook.md",
        root / "mainnet-proof-and-rollback-runbook.md",
        root / "incident-response-247-drill.md",
        root / "reconciliation-load-chaos-slos.md",
    ]
    for path in files:
        path.write_text("# placeholder\n", encoding="utf-8")


def test_ops_evidence_generator_writes_artifact(tmp_path: Path) -> None:
    drill = {
        "drill_id": "drill_1",
        "scenario": "turnkey_outage",
        "incident_started_at": "2026-02-26T09:00:00Z",
        "failover_mode_activated_at": "2026-02-26T09:10:00Z",
        "primary_recovered_at": "2026-02-26T09:40:00Z",
        "measured_rpo_seconds": 0,
    }
    drill_path = tmp_path / "drill.json"
    drill_path.write_text(json.dumps(drill), encoding="utf-8")

    runbook_root = tmp_path / "docs" / "design-partner"
    runbook_root.mkdir(parents=True, exist_ok=True)
    _write_runbooks(runbook_root)

    output_path = tmp_path / "ops-readiness.json"
    env = dict(os.environ)
    env["PAGERDUTY_ROUTING_KEY"] = "pd_test"
    env["SARDIS_ALERT_SEVERITY_CHANNELS_JSON"] = json.dumps({"critical": ["pagerduty"]})
    env["SARDIS_ALERT_CHANNEL_COOLDOWNS_JSON"] = json.dumps({"pagerduty": 60})

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            "--drill-evidence",
            str(drill_path),
            "--output",
            str(output_path),
            "--max-failover-rto-min",
            "15",
            "--max-recovery-rto-min",
            "60",
            "--max-rpo-sec",
            "0",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["drill"]["checks"]["failover_rto_within_target"] is True
    assert payload["alert_routing"]["pagerduty_configured"] is True


def test_ops_evidence_generator_fails_on_threshold_breach(tmp_path: Path) -> None:
    drill = {
        "drill_id": "drill_2",
        "incident_started_at": "2026-02-26T09:00:00Z",
        "failover_mode_activated_at": "2026-02-26T10:10:00Z",
        "primary_recovered_at": "2026-02-26T12:00:00Z",
        "measured_rpo_seconds": 120,
    }
    drill_path = tmp_path / "drill.json"
    drill_path.write_text(json.dumps(drill), encoding="utf-8")

    runbook_root = tmp_path / "docs" / "design-partner"
    runbook_root.mkdir(parents=True, exist_ok=True)
    _write_runbooks(runbook_root)

    output_path = tmp_path / "ops-readiness.json"
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            "--drill-evidence",
            str(drill_path),
            "--output",
            str(output_path),
            "--max-failover-rto-min",
            "15",
            "--max-recovery-rto-min",
            "60",
            "--max-rpo-sec",
            "0",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "drill metrics exceed configured thresholds" in (result.stdout + result.stderr)
