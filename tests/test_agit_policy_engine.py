"""Tests for AGIT Policy Engine — hash-chained policy tracking."""
from __future__ import annotations

import pytest
from sardis_v2_core.agit_policy_engine import (
    AgitPolicyEngine,
    PolicyChainVerification,
    PolicyCommit,
)


@pytest.fixture
def engine():
    """Fresh in-memory AGIT policy engine."""
    return AgitPolicyEngine(repo_path=":memory:", agent_id="test-policy")


def test_commit_policy_creates_hash(engine):
    """Commit a policy and verify it returns a PolicyCommit with hash."""
    commit = engine.commit_policy(
        agent_id="agent_001",
        policy_dict={"limit_per_tx": "500", "daily_limit": "1000"},
    )

    assert isinstance(commit, PolicyCommit)
    assert len(commit.commit_hash) == 64  # SHA-256 hex
    assert commit.agent_id == "agent_001"
    assert commit.signed is False
    assert commit.signer_did is None


def test_commit_policy_unique_hashes(engine):
    """Different policies produce different hashes."""
    c1 = engine.commit_policy("agent_001", {"limit_per_tx": "100"})
    c2 = engine.commit_policy("agent_001", {"limit_per_tx": "200"})

    assert c1.commit_hash != c2.commit_hash


def test_commit_policy_same_agent_chains(engine):
    """Multiple commits to same agent form a chain."""
    c1 = engine.commit_policy("agent_001", {"v": 1})
    c2 = engine.commit_policy("agent_001", {"v": 2})
    c3 = engine.commit_policy("agent_001", {"v": 3})

    history = engine.get_chain_history("agent_001")
    assert len(history) == 3
    # Most recent first
    assert history[0]["commit_hash"] == c3.commit_hash
    assert history[2]["commit_hash"] == c1.commit_hash


def test_verify_chain_valid(engine):
    """Multi-commit chain passes verification."""
    engine.commit_policy("agent_001", {"v": 1})
    engine.commit_policy("agent_001", {"v": 2})
    engine.commit_policy("agent_001", {"v": 3})

    verification = engine.verify_policy_chain("agent_001")

    assert verification.valid is True
    assert verification.chain_length == 3
    assert verification.broken_at is None
    assert verification.error is None


def test_verify_chain_empty(engine):
    """Empty chain is valid."""
    verification = engine.verify_policy_chain("nonexistent_agent")

    assert verification.valid is True
    assert verification.chain_length == 0


def test_tampered_chain_detected(engine):
    """Modify committed state -> verification fails."""
    engine.commit_policy("agent_001", {"v": 1})
    engine.commit_policy("agent_001", {"v": 2})

    # Tamper with the chain
    chain = engine._chains["agent_001"]
    chain[1]["hash"] = "0" * 64  # corrupt the hash

    verification = engine.verify_policy_chain("agent_001")

    assert verification.valid is False
    assert verification.broken_at is not None


def test_tampered_state_detected(engine):
    """Modify the stored state -> hash mismatch detected."""
    engine.commit_policy("agent_001", {"v": 1})

    # Tamper with the state
    chain = engine._chains["agent_001"]
    chain[0]["state"]["memory"]["policy"]["v"] = 999

    verification = engine.verify_policy_chain("agent_001")

    assert verification.valid is False
    assert verification.broken_at == 0
    assert "Hash mismatch" in (verification.error or "")


def test_get_policy_at(engine):
    """Retrieve policy at a specific commit."""
    c1 = engine.commit_policy("agent_001", {"limit": "100"})
    c2 = engine.commit_policy("agent_001", {"limit": "500"})

    policy1 = engine.get_policy_at(c1.commit_hash)
    policy2 = engine.get_policy_at(c2.commit_hash)

    assert policy1 == {"limit": "100"}
    assert policy2 == {"limit": "500"}


def test_get_policy_at_not_found(engine):
    """Nonexistent commit hash returns None."""
    result = engine.get_policy_at("nonexistent_hash")
    assert result is None


def test_policy_diff(engine):
    """Diff between two commits shows changes."""
    c1 = engine.commit_policy("agent_001", {"limit": "100", "daily": "500"})
    c2 = engine.commit_policy("agent_001", {"limit": "200", "monthly": "5000"})

    diff = engine.diff_policies(c1.commit_hash, c2.commit_hash)

    assert diff["changed"] == {"limit": {"old": "100", "new": "200"}}
    assert diff["added"] == {"monthly": "5000"}
    assert diff["removed"] == {"daily": "500"}


def test_policy_diff_identical(engine):
    """Diff of same hash returns empty diff."""
    c1 = engine.commit_policy("agent_001", {"limit": "100"})

    diff = engine.diff_policies(c1.commit_hash, c1.commit_hash)

    assert diff["added"] == {}
    assert diff["removed"] == {}
    assert diff["changed"] == {}


def test_chain_history_limit(engine):
    """History respects limit parameter."""
    for i in range(10):
        engine.commit_policy("agent_001", {"v": i})

    history = engine.get_chain_history("agent_001", limit=3)
    assert len(history) == 3


def test_agit_failure_non_blocking(engine):
    """Engine failures don't prevent policy operations."""
    # The in-memory fallback should always work
    commit = engine.commit_policy("agent_001", {"test": True})
    assert commit.commit_hash is not None

    verification = engine.verify_policy_chain("agent_001")
    assert verification.valid is True


def test_separate_agent_chains(engine):
    """Different agents have independent chains."""
    engine.commit_policy("agent_001", {"v": 1})
    engine.commit_policy("agent_002", {"v": 1})

    v1 = engine.verify_policy_chain("agent_001")
    v2 = engine.verify_policy_chain("agent_002")

    assert v1.chain_length == 1
    assert v2.chain_length == 1
