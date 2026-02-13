from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_openai_example_uses_supported_sdk_methods() -> None:
    content = _read("examples/openai_agents_payment.py")
    assert "sardis.wallets.transfer(" in content
    assert "sardis.agents.create(" in content
    assert "sardis.payments.send(" not in content


def test_langchain_example_uses_supported_sdk_methods() -> None:
    content = _read("examples/langchain_sardis_agent.py")
    assert "sardis.wallets.transfer(" in content
    assert "sardis.wallets.get_balance(" in content
    assert "sardis.payments.send(" not in content


def test_crewai_example_uses_supported_sdk_methods() -> None:
    content = _read("examples/crewai_finance_team.py")
    assert "sardis.groups.create(" in content
    assert "sardis.groups.add_agent(" in content
    assert "sardis.wallets.transfer(" in content
    assert "sardis.payments.send(" not in content
    assert "get_status(" not in content


def test_vercel_example_uses_supported_sdk_methods() -> None:
    content = _read("examples/vercel_ai_payment.ts")
    assert "sardis.agents.create(" in content
    assert "sardis.wallets.create({" in content
    assert "sardis.wallets.transfer(" in content
    assert "sardis.payments.send(" not in content
