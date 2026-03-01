"""OpenClaw skill base classes and models."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillContext:
    """Execution context for an OpenClaw skill."""
    api_key: str
    wallet_id: str
    agent_id: str
    base_url: str = "https://api.sardis.sh/v2"


@dataclass
class SkillResult:
    """Result of an OpenClaw skill execution."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class OpenClawSkill(ABC):
    """Abstract base class for executable OpenClaw skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> list[str]:
        """List of accepted parameter names."""
        ...

    @property
    @abstractmethod
    def required_permissions(self) -> list[str]:
        """Permissions needed to execute this skill."""
        ...

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        """Execute the skill with the given parameters and context."""
        ...

    def validate_params(self, params: dict[str, Any]) -> str | None:
        """Validate parameters. Returns error message or None if valid."""
        missing = [p for p in self.parameters if p not in params]
        if missing:
            return f"Missing required parameters: {', '.join(missing)}"
        return None
