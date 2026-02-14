from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readme_python_quickstart_uses_supported_calls() -> None:
    readme = _read("README.md")

    assert "agent = client.agents.create(" in readme
    assert "wallet = client.wallets.create(" in readme
    assert "tx = client.wallets.transfer(" in readme

    py_agents = _read("packages/sardis-sdk-python/src/sardis_sdk/resources/agents.py")
    py_wallets = _read("packages/sardis-sdk-python/src/sardis_sdk/resources/wallets.py")

    assert "def create(" in py_agents
    assert "def create(" in py_wallets
    assert "def transfer(" in py_wallets


def test_readme_typescript_quickstart_uses_supported_calls() -> None:
    readme = _read("README.md")

    assert "const agent = await client.agents.create(" in readme
    assert "const wallet = await client.wallets.create(" in readme
    assert "const tx = await client.wallets.transfer(" in readme

    ts_agents = _read("packages/sardis-sdk-js/src/resources/agents.ts")
    ts_wallets = _read("packages/sardis-sdk-js/src/resources/wallets.ts")

    assert "async create(" in ts_agents
    assert "async create(" in ts_wallets
    assert "async transfer(" in ts_wallets
