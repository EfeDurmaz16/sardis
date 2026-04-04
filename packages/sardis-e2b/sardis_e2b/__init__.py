"""Sardis E2B sandbox helpers.

Convenience functions for creating and running Sardis-enabled AI agents
inside E2B sandboxes. Import is safe even without the ``e2b`` package
installed -- the dependency is loaded lazily when functions are called.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEMPLATE_NAME: str = "sardis-agent"
DEFAULT_WORKDIR: str = "/home/user"

# ---------------------------------------------------------------------------
# Lazy E2B import
# ---------------------------------------------------------------------------

_Sandbox: Any = None


def _get_sandbox_class() -> Any:
    """Return the E2B ``Sandbox`` class, importing it on first use."""
    global _Sandbox
    if _Sandbox is not None:
        return _Sandbox
    try:
        from e2b import Sandbox  # type: ignore[import-untyped]

        _Sandbox = Sandbox
        return _Sandbox
    except ImportError as exc:
        raise ImportError(
            "The 'e2b' package is required to create sandboxes. "
            "Install it with:  pip install e2b"
        ) from exc


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def create_sandbox(
    api_key: str | None = None,
    simulation: bool = True,
    *,
    template: str = TEMPLATE_NAME,
    timeout: int = 60,
    extra_env: dict[str, str] | None = None,
) -> Any:
    """Create an E2B sandbox with the Sardis agent template.

    Parameters
    ----------
    api_key:
        Sardis API key. When provided it is passed as the
        ``SARDIS_API_KEY`` environment variable inside the sandbox.
    simulation:
        If ``True`` (the default), the sandbox runs in simulation mode
        so no real on-chain transactions are submitted.
    template:
        E2B template name. Defaults to ``sardis-agent``.
    timeout:
        Sandbox creation timeout in seconds.
    extra_env:
        Additional environment variables to inject into the sandbox.

    Returns
    -------
    e2b.Sandbox
        A running sandbox instance. Use it as a context manager or call
        ``.close()`` when done.
    """
    Sandbox = _get_sandbox_class()

    env_vars: dict[str, str] = {
        "SARDIS_SIMULATION": str(simulation).lower(),
    }

    if api_key is not None:
        env_vars["SARDIS_API_KEY"] = api_key

    if extra_env:
        env_vars.update(extra_env)

    return Sandbox(
        template=template,
        env_vars=env_vars,
        timeout=timeout,
    )


@dataclass
class SandboxResult:
    """Outcome of running agent code inside an E2B sandbox."""

    stdout: str
    stderr: str
    exit_code: int


def run_agent_in_sandbox(
    agent_code: str,
    api_key: str | None = None,
    simulation: bool = True,
    *,
    template: str = TEMPLATE_NAME,
    timeout: int = 60,
    extra_env: dict[str, str] | None = None,
) -> SandboxResult:
    """Create a sandbox, run *agent_code*, and return the output.

    This is the simplest way to execute arbitrary Sardis agent code in an
    isolated environment.

    Parameters
    ----------
    agent_code:
        Python source code to execute inside the sandbox.
    api_key:
        Sardis API key (optional).
    simulation:
        Run in simulation mode (default ``True``).
    template:
        E2B template name.
    timeout:
        Sandbox creation timeout in seconds.
    extra_env:
        Additional environment variables.

    Returns
    -------
    SandboxResult
        Contains ``stdout``, ``stderr``, and ``exit_code``.
    """
    sandbox = create_sandbox(
        api_key=api_key,
        simulation=simulation,
        template=template,
        timeout=timeout,
        extra_env=extra_env,
    )

    try:
        agent_path = f"{DEFAULT_WORKDIR}/agent.py"
        sandbox.filesystem.write(agent_path, agent_code)

        proc = sandbox.process.start(f"python {agent_path}")
        proc.wait()

        return SandboxResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.exit_code,
        )
    finally:
        sandbox.close()


__all__ = [
    "TEMPLATE_NAME",
    "DEFAULT_WORKDIR",
    "SandboxResult",
    "create_sandbox",
    "run_agent_in_sandbox",
]
