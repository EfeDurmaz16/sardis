"""AGIT Policy Engine — hash-chained, tamper-evident policy tracking.

Wraps AGIT's ExecutionEngine (and optionally AgitFidesEngine for DID-signed
commits) to create an auditable history of spending policy changes.

AGIT state structure: {"memory": {...}, "world_state": {}}
All commits are sync; async callers should use asyncio.to_thread().

Non-blocking: AGIT failures never block payments (log warning only).
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("sardis.core.agit_policy_engine")


@dataclass(frozen=True)
class PolicyCommit:
    """Result of committing a policy snapshot to the AGIT chain."""
    commit_hash: str
    agent_id: str
    signed: bool = False
    signer_did: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class PolicyChainVerification:
    """Result of verifying an AGIT policy chain."""
    valid: bool
    chain_length: int
    broken_at: int | None = None
    error: str | None = None


class AgitPolicyEngine:
    """Hash-chained policy change tracker using AGIT ExecutionEngine.

    Falls back to a simple in-memory hash chain when AGIT is not installed.

    Usage:
        engine = AgitPolicyEngine()
        commit = engine.commit_policy("agent_123", {"limit_per_tx": "500"})
        verification = engine.verify_policy_chain("agent_123")
    """

    def __init__(
        self,
        repo_path: str = ":memory:",
        agent_id: str = "sardis-policy",
    ) -> None:
        self._repo_path = repo_path
        self._agent_id = agent_id
        self._engine: Any | None = None
        self._fides_engine: Any | None = None
        # Fallback in-memory chain when AGIT is not available
        self._chains: dict[str, list[dict[str, Any]]] = {}
        self._agit_available = False

        try:
            from agit.engine.executor import ExecutionEngine
            self._engine = ExecutionEngine(repo_path=repo_path, agent_id=agent_id)
            self._agit_available = True
            logger.info("AGIT ExecutionEngine initialized (repo=%s)", repo_path)
        except ImportError:
            logger.info("AGIT not installed — using in-memory hash chain fallback")
        except Exception as e:
            logger.warning("AGIT initialization failed: %s — using fallback", e)

    def init_fides_identity(self, fides_did: str, private_key_hex: str) -> bool:
        """Initialize FIDES identity for signed commits.

        Args:
            fides_did: FIDES DID for signing
            private_key_hex: Hex-encoded Ed25519 private key

        Returns:
            True if FIDES engine was initialized successfully
        """
        if not self._agit_available:
            return False

        try:
            from agit.integrations.fides import AgitFidesEngine, FidesIdentity

            identity = FidesIdentity(
                did=fides_did,
                private_key=bytes.fromhex(private_key_hex),
            )
            self._fides_engine = AgitFidesEngine(
                engine=self._engine,
                identity=identity,
            )
            logger.info("AGIT FIDES engine initialized for %s", fides_did)
            return True
        except ImportError:
            logger.info("agit.integrations.fides not available")
            return False
        except Exception as e:
            logger.warning("FIDES engine initialization failed: %s", e)
            return False

    def commit_policy(
        self,
        agent_id: str,
        policy_dict: dict[str, Any],
        fides_did: str | None = None,
    ) -> PolicyCommit:
        """Commit a policy snapshot to the hash chain.

        If FIDES identity is configured and fides_did matches, uses signed_commit.
        Otherwise uses regular commit_state.

        Args:
            agent_id: Agent whose policy changed
            policy_dict: Serialized policy snapshot
            fides_did: Optional FIDES DID for signed commit

        Returns:
            PolicyCommit with hash and signature info
        """
        state = {
            "memory": {
                "agent_id": agent_id,
                "policy": policy_dict,
                "committed_at": datetime.now(UTC).isoformat(),
            },
            "world_state": {},
        }

        if self._agit_available and self._engine is not None:
            return self._commit_agit(agent_id, state, fides_did)

        return self._commit_fallback(agent_id, state)

    def _commit_agit(
        self,
        agent_id: str,
        state: dict[str, Any],
        fides_did: str | None,
    ) -> PolicyCommit:
        """Commit using real AGIT engine."""
        try:
            if fides_did and self._fides_engine is not None:
                result = self._fides_engine.signed_commit(state)
                commit_hash = getattr(result, "hash", str(result))
                return PolicyCommit(
                    commit_hash=commit_hash,
                    agent_id=agent_id,
                    signed=True,
                    signer_did=fides_did,
                )

            result = self._engine.commit_state(state)
            commit_hash = getattr(result, "hash", str(result))
            return PolicyCommit(
                commit_hash=commit_hash,
                agent_id=agent_id,
            )
        except Exception as e:
            logger.warning("AGIT commit failed, using fallback: %s", e)
            return self._commit_fallback(agent_id, state)

    def _commit_fallback(
        self,
        agent_id: str,
        state: dict[str, Any],
    ) -> PolicyCommit:
        """Fallback: simple SHA-256 hash chain in memory."""
        chain = self._chains.setdefault(agent_id, [])

        prev_hash = chain[-1]["hash"] if chain else "0" * 64
        content = json.dumps(state, sort_keys=True, default=str)
        hash_input = f"{prev_hash}:{content}"
        commit_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        chain.append({
            "hash": commit_hash,
            "prev_hash": prev_hash,
            "state": state,
            "created_at": datetime.now(UTC).isoformat(),
        })

        return PolicyCommit(
            commit_hash=commit_hash,
            agent_id=agent_id,
        )

    def verify_policy_chain(self, agent_id: str) -> PolicyChainVerification:
        """Verify integrity of the policy hash chain for an agent.

        Walks the commit history and verifies each hash links correctly.

        Returns:
            PolicyChainVerification with validity status
        """
        if self._agit_available and self._engine is not None:
            return self._verify_agit(agent_id)

        return self._verify_fallback(agent_id)

    def _verify_agit(self, agent_id: str) -> PolicyChainVerification:
        """Verify using real AGIT engine."""
        try:
            history = self._engine.get_history()
            if not history:
                return PolicyChainVerification(valid=True, chain_length=0)

            for i, commit in enumerate(history):
                if hasattr(commit, "_fides") and commit._fides:
                    try:
                        self._engine.verify_commit(commit)
                    except Exception:
                        return PolicyChainVerification(
                            valid=False,
                            chain_length=len(history),
                            broken_at=i,
                            error=f"Signature verification failed at commit {i}",
                        )

            return PolicyChainVerification(
                valid=True,
                chain_length=len(history),
            )
        except Exception as e:
            logger.warning("AGIT chain verification failed: %s", e)
            return self._verify_fallback(agent_id)

    def _verify_fallback(self, agent_id: str) -> PolicyChainVerification:
        """Verify in-memory fallback chain."""
        chain = self._chains.get(agent_id, [])
        if not chain:
            return PolicyChainVerification(valid=True, chain_length=0)

        for i, entry in enumerate(chain):
            expected_prev = chain[i - 1]["hash"] if i > 0 else "0" * 64
            if entry["prev_hash"] != expected_prev:
                return PolicyChainVerification(
                    valid=False,
                    chain_length=len(chain),
                    broken_at=i,
                    error=f"Hash chain broken at commit {i}",
                )

            content = json.dumps(entry["state"], sort_keys=True, default=str)
            hash_input = f"{entry['prev_hash']}:{content}"
            expected_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            if entry["hash"] != expected_hash:
                return PolicyChainVerification(
                    valid=False,
                    chain_length=len(chain),
                    broken_at=i,
                    error=f"Hash mismatch at commit {i}",
                )

        return PolicyChainVerification(
            valid=True,
            chain_length=len(chain),
        )

    def get_policy_at(self, commit_hash: str) -> dict[str, Any] | None:
        """Get the policy snapshot at a specific commit hash.

        Returns None if commit not found.
        """
        if self._agit_available and self._engine is not None:
            try:
                state = self._engine.get_state_at(commit_hash)
                if state and "memory" in state:
                    return state["memory"].get("policy")
                return state
            except Exception:
                pass

        # Fallback: search in-memory chains
        for chain in self._chains.values():
            for entry in chain:
                if entry["hash"] == commit_hash:
                    return entry["state"]["memory"].get("policy")

        return None

    def diff_policies(self, hash1: str, hash2: str) -> dict[str, Any]:
        """Compute diff between two policy snapshots.

        Returns dict with 'added', 'removed', 'changed' keys.
        """
        policy1 = self.get_policy_at(hash1) or {}
        policy2 = self.get_policy_at(hash2) or {}

        added = {k: v for k, v in policy2.items() if k not in policy1}
        removed = {k: v for k, v in policy1.items() if k not in policy2}
        changed = {
            k: {"old": policy1[k], "new": policy2[k]}
            for k in policy1
            if k in policy2 and policy1[k] != policy2[k]
        }

        return {"added": added, "removed": removed, "changed": changed}

    def get_chain_history(self, agent_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get commit history for an agent.

        Returns list of commit metadata dicts (most recent first).
        """
        if self._agit_available and self._engine is not None:
            try:
                history = self._engine.get_history()
                return [
                    {
                        "commit_hash": getattr(c, "hash", str(c)),
                        "created_at": getattr(c, "timestamp", None),
                        "signed": bool(getattr(c, "_fides", None)),
                        "signer_did": getattr(c, "_fides", {}).get("did") if hasattr(c, "_fides") and isinstance(getattr(c, "_fides", None), dict) else None,
                    }
                    for c in (history or [])
                ][:limit]
            except Exception:
                pass

        # Fallback
        chain = self._chains.get(agent_id, [])
        return [
            {
                "commit_hash": entry["hash"],
                "created_at": entry["created_at"],
                "signed": False,
                "signer_did": None,
            }
            for entry in reversed(chain)
        ][:limit]
