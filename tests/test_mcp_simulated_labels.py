"""Tests to verify all MCP server simulated responses contain _simulated markers.

Every tool that returns fabricated financial data in simulated mode MUST include:
  _simulated: true
  _warning: "This is simulated data. Configure SARDIS_API_KEY for real data."

This prevents LLMs from mistaking fake balances, transactions, and approvals
for real financial data.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "packages" / "sardis-mcp-server" / "src" / "tools"

# Files that contain no simulated financial data (pure definitions, routing, etc.)
EXCLUDED_FILES = {"types.ts", "index.ts"}


def _get_tool_files() -> list[Path]:
    """Return all .ts tool files that may contain simulated responses."""
    return sorted(
        p for p in TOOLS_DIR.glob("*.ts")
        if p.name not in EXCLUDED_FILES
    )


def _extract_simulated_blocks(content: str) -> list[tuple[int, str]]:
    """Extract code blocks that are inside simulated-mode conditionals.

    Returns a list of (line_number, block_text) tuples.
    """
    blocks: list[tuple[int, str]] = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect simulated block entry
        if ("!config.apiKey" in line and ("simulated" in line or i + 1 < len(lines) and "simulated" in lines[i + 1])):
            # Collect the block until the brace depth returns to 0
            block_start = i
            depth = 0
            block_lines = []
            for j in range(i, len(lines)):
                block_lines.append(lines[j])
                depth += lines[j].count("{") - lines[j].count("}")
                if depth <= 0 and j > i:
                    break
            blocks.append((block_start + 1, "\n".join(block_lines)))
            i = j + 1 if "j" in dir() else i + 1
            continue
        i += 1
    return blocks


def _block_returns_json(block: str) -> bool:
    """Check if a simulated block returns structured JSON data (not just error text)."""
    return "JSON.stringify" in block or "serialize" in block


class TestMCPSimulatedLabels:
    """Verify all simulated mode responses are clearly marked."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.tool_files = _get_tool_files()
        assert len(self.tool_files) > 0, "No tool files found"

    def test_tool_files_exist(self):
        """Sanity check: we found the expected tool files."""
        names = {p.name for p in self.tool_files}
        assert "payments.ts" in names
        assert "wallets.ts" in names
        assert "fiat.ts" in names
        assert "approvals.ts" in names
        assert "guardrails.ts" in names

    @pytest.mark.parametrize("tool_file", _get_tool_files(), ids=lambda p: p.name)
    def test_simulated_blocks_have_marker(self, tool_file: Path):
        """Every simulated block that returns JSON must contain _simulated marker."""
        content = tool_file.read_text()
        blocks = _extract_simulated_blocks(content)

        for line_no, block in blocks:
            if not _block_returns_json(block):
                continue  # Skip blocks that return plain text errors

            has_marker = "_simulated" in block or "serializeSimulated" in block
            assert has_marker, (
                f"{tool_file.name}:{line_no} — Simulated block returns JSON "
                f"without _simulated marker. Block preview:\n"
                f"{block[:300]}..."
            )

    def test_no_math_random_in_approval_status(self):
        """approvals.ts must not use Math.random() for approval status."""
        content = (TOOLS_DIR / "approvals.ts").read_text()
        # Strip comments before checking — Math.random() in comments is fine
        code_lines = [
            line for line in content.split("\n")
            if not line.strip().startswith("//") and not line.strip().startswith("*")
        ]
        code_only = "\n".join(code_lines)
        assert "Math.random()" not in code_only, (
            "approvals.ts still uses Math.random() for approval status in executable code. "
            "Use deterministic 'simulated_pending' instead."
        )

    def test_approval_status_is_deterministic(self):
        """approvals.ts simulated get_approval_status must return 'simulated_pending'."""
        content = (TOOLS_DIR / "approvals.ts").read_text()
        assert "simulated_pending" in content, (
            "approvals.ts should return 'simulated_pending' as the deterministic "
            "status for simulated approval checks."
        )

    def test_fiat_live_mode_list_returns_error(self):
        """fiat.ts list_funding_transactions in live mode must return an error, not silent empty."""
        content = (TOOLS_DIR / "fiat.ts").read_text()
        # Find the handler implementation (second occurrence, after the tool definition)
        parts = content.split("sardis_list_funding_transactions")
        # The handler is in the third part (after definition name and handler key)
        handler_section = "sardis_list_funding_transactions".join(parts[2:]) if len(parts) > 2 else parts[-1]
        # Get just the handler body before the next handler
        handler_body = handler_section.split("\n\n  sardis_")[0] if "\n\n  sardis_" in handler_section else handler_section[:2000]
        assert "isError: true" in handler_body, (
            "fiat.ts sardis_list_funding_transactions live mode should return isError: true "
            "since the endpoint is not implemented."
        )

    def test_spending_trends_no_random(self):
        """spending.ts trends must not use Math.random() for financial amounts."""
        content = (TOOLS_DIR / "spending.ts").read_text()
        # Find the trends simulated block
        trends_section = content.split("sardis_get_spending_trends")[1] if "sardis_get_spending_trends" in content else ""
        assert "Math.random()" not in trends_section, (
            "spending.ts spending trends still uses Math.random() for financial amounts. "
            "Use deterministic values instead."
        )

    def test_wallets_zero_address_has_marker(self):
        """wallets.ts simulated balance with zero address must have _simulated."""
        content = (TOOLS_DIR / "wallets.ts").read_text()
        assert "_simulated" in content, (
            "wallets.ts simulated responses must include _simulated marker."
        )

    def test_guardrails_mock_data_has_marker(self):
        """guardrails.ts mock circuit breaker/rate limit data must have _simulated."""
        content = (TOOLS_DIR / "guardrails.ts").read_text()
        assert content.count("_simulated") >= 5, (
            "guardrails.ts should have _simulated markers on all 5 simulated responses "
            f"(circuit breaker, kill switch activate/deactivate, rate limits, alerts). "
            f"Found {content.count('_simulated')}."
        )

    def test_fiat_multi_balance_has_marker(self):
        """fiat.ts multi-balance with $500K+ fabricated amounts must have _simulated."""
        content = (TOOLS_DIR / "fiat.ts").read_text()
        # Find all occurrences and check the handler (last occurrence context)
        parts = content.split("sardis_get_multi_balance")
        assert len(parts) >= 3, "Expected sardis_get_multi_balance in definition and handler"
        # Handler section is after the second occurrence
        handler_section = parts[-1][:2000]
        assert "_simulated" in handler_section or "serializeSimulated" in handler_section, (
            "fiat.ts sardis_get_multi_balance simulated response with $500K+ balances "
            "must include _simulated marker."
        )
