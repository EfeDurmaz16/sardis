"""Credential-free checks for the Sardis E2B template package."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest
import sardis_e2b

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_e2b_template_manifest_points_to_tracked_dockerfile():
    data = tomllib.loads((PACKAGE_ROOT / "e2b.toml").read_text(encoding="utf-8"))

    assert data["template"]["name"] == "sardis-agent"
    assert data["template"]["dockerfile"] == "e2b.Dockerfile"
    assert (PACKAGE_ROOT / data["template"]["dockerfile"]).is_file()
    assert "sardis" in data["template"]["metadata"]["tags"]


def test_dockerfile_keeps_simulation_mode_and_healthcheck():
    dockerfile = (PACKAGE_ROOT / "e2b.Dockerfile").read_text(encoding="utf-8")

    assert "ENV SARDIS_SIMULATION=true" in dockerfile
    assert "COPY sardis_e2b/ /opt/sardis_e2b/" in dockerfile
    assert "sardis-healthcheck" in dockerfile
    assert "RUN python3 /usr/local/bin/sardis-healthcheck" in dockerfile


def test_helper_import_is_safe_without_e2b_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "e2b", None)
    monkeypatch.setattr(sardis_e2b, "_Sandbox", None)

    with pytest.raises(ImportError, match="pip install e2b"):
        sardis_e2b.create_sandbox()


def test_run_agent_in_sandbox_uses_template_and_simulation_env(monkeypatch):
    calls = {}

    class FakeFilesystem:
        def write(self, path, code):
            calls["path"] = path
            calls["code"] = code

    class FakeProcessHandle:
        stdout = "ok"
        stderr = ""
        exit_code = 0

        def wait(self):
            calls["waited"] = True

    class FakeProcess:
        def start(self, command):
            calls["command"] = command
            return FakeProcessHandle()

    class FakeSandbox:
        def __init__(self, **kwargs):
            calls["sandbox_kwargs"] = kwargs
            self.filesystem = FakeFilesystem()
            self.process = FakeProcess()

        def close(self):
            calls["closed"] = True

    monkeypatch.setattr(sardis_e2b, "_Sandbox", FakeSandbox)

    result = sardis_e2b.run_agent_in_sandbox("print('hello')", extra_env={"EXTRA": "1"})

    assert calls["sandbox_kwargs"]["template"] == "sardis-agent"
    assert calls["sandbox_kwargs"]["env_vars"] == {
        "SARDIS_SIMULATION": "true",
        "EXTRA": "1",
    }
    assert calls["path"] == "/home/user/agent.py"
    assert calls["command"] == "python /home/user/agent.py"
    assert calls["waited"] is True
    assert calls["closed"] is True
    assert result.stdout == "ok"
    assert result.stderr == ""
    assert result.exit_code == 0
