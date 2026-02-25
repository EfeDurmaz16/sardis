from __future__ import annotations

from sardis_api.routers import a2a


def test_a2a_trust_table_disabled_allows_relation(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "0")
    allowed, reason = a2a._check_a2a_trust_relation("agent_a", "agent_b")
    assert allowed is True
    assert reason == "trust_table_not_enforced"


def test_a2a_trust_table_requires_configuration_when_enforced(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.delenv("SARDIS_A2A_TRUST_RELATIONS", raising=False)
    allowed, reason = a2a._check_a2a_trust_relation("agent_a", "agent_b")
    assert allowed is False
    assert reason == "a2a_trust_table_not_configured"


def test_a2a_trust_table_allows_explicit_relation(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "agent_a>agent_b|agent_c,agent_b>agent_a")
    allowed, reason = a2a._check_a2a_trust_relation("agent_a", "agent_c")
    assert allowed is True
    assert reason == "trusted_sender_relation"


def test_a2a_trust_table_allows_wildcard_sender(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "*>agent_ops")
    allowed, reason = a2a._check_a2a_trust_relation("agent_x", "agent_ops")
    assert allowed is True
    assert reason == "trusted_wildcard_relation"


def test_a2a_trust_table_rejects_untrusted_pair(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "agent_a>agent_b")
    allowed, reason = a2a._check_a2a_trust_relation("agent_a", "agent_d")
    assert allowed is False
    assert reason == "a2a_agent_not_trusted"
