from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_tabletop_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "facility_gate_pilot_tabletop.py"
    )
    spec = importlib.util.spec_from_file_location("facility_gate_pilot_tabletop", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_facility_gate_pilot_tabletop_harness_passes() -> None:
    module = _load_tabletop_module()

    report = module.run_tabletop()

    assert report["schema_version"] == "facility_gate_pilot_tabletop_v1"
    assert report["status"] == "passed"
    assert all(report["checks"].values())
    assert report["checks"]["duplicate_execute_idempotent"] is True
    assert report["checks"]["projection_replay_clean"] is True
    assert report["artifacts"]["decision_packet_hash"]
    assert report["artifacts"]["replay"]["drifted"] == 0
