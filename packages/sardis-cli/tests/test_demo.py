"""Tests for the demo CLI command and degraded state handlers."""
from __future__ import annotations

import socket

import pytest
from click.testing import CliRunner

from sardis_cli.commands.demo import (
    _find_free_port,
    _start_merchant_server,
    handle_faucet_empty,
    handle_no_network,
    handle_port_in_use,
    handle_rpc_down,
    handle_wallet_creation_failure,
    show_post_payment_experience,
)
from sardis_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestDemoCommand:
    """Test the demo command starts and produces expected output."""

    def test_demo_runs_without_error(self, runner):
        result = runner.invoke(cli, ["demo"], obj={"config": {}})
        assert result.exit_code == 0
        assert "Sardis Demo" in result.output
        assert "Sandbox" in result.output

    def test_demo_with_chain_option(self, runner):
        result = runner.invoke(cli, ["demo", "--chain", "base_sepolia"], obj={"config": {}})
        assert result.exit_code == 0
        assert "base_sepolia" in result.output

    def test_demo_generates_api_key(self, runner):
        result = runner.invoke(cli, ["demo"], obj={"config": {}})
        assert result.exit_code == 0
        assert "API key" in result.output or "sk_demo" in result.output

    def test_demo_creates_mandates(self, runner):
        result = runner.invoke(cli, ["demo"], obj={"config": {}})
        assert result.exit_code == 0
        assert "dev-tools" in result.output
        assert "api-payments" in result.output
        assert "no-crypto" in result.output

    def test_demo_starts_merchant_server(self, runner):
        result = runner.invoke(cli, ["demo", "--port", "18402"], obj={"config": {}})
        assert result.exit_code == 0
        # Should report merchant server status
        assert "merchant" in result.output.lower() or "localhost" in result.output.lower()


class TestMockMerchant:
    """Test the mock merchant server."""

    def test_find_free_port_returns_available(self):
        port = _find_free_port(19000, 19010)
        assert port is not None
        assert 19000 <= port <= 19010

    def test_find_free_port_skips_used(self):
        # Bind a port to make it unavailable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 19100))
        try:
            port = _find_free_port(19100, 19105)
            assert port is not None
            assert port > 19100  # Should skip the bound port
        finally:
            sock.close()

    def test_find_free_port_returns_none_when_exhausted(self):
        sockets = []
        try:
            for p in range(19200, 19203):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(("127.0.0.1", p))
                sockets.append(s)
            result = _find_free_port(19200, 19202)
            assert result is None
        finally:
            for s in sockets:
                s.close()

    def test_start_merchant_server(self):
        port = _find_free_port(19300, 19310)
        assert port is not None
        server = _start_merchant_server(port)
        assert server is not None
        server.shutdown()


class TestDegradedStates:
    """Test degraded state handlers."""

    def test_wallet_creation_failure_returns_fallback(self):
        result = handle_wallet_creation_failure("base_sepolia")
        assert "wallet_id" in result
        assert "address" in result
        assert result["wallet_id"].startswith("wal_fallback_")

    def test_faucet_empty_suggests_base_sepolia(self, capsys):
        handle_faucet_empty("tempo_moderato")
        captured = capsys.readouterr()
        assert "base_sepolia" in captured.out

    def test_faucet_empty_base_sepolia_no_redirect(self, capsys):
        handle_faucet_empty("base_sepolia")
        captured = capsys.readouterr()
        assert "temporarily unavailable" in captured.out

    def test_port_in_use_returns_alternative(self):
        result = handle_port_in_use(19400)
        assert result is not None

    def test_rpc_down_returns_false(self):
        result = handle_rpc_down("base_sepolia", max_retries=1)
        assert result is False

    def test_no_network_shows_panel(self, capsys):
        handle_no_network()
        captured = capsys.readouterr()
        assert "No Network" in captured.out or "offline" in captured.out.lower() or "Offline" in captured.out


class TestPostPaymentExperience:
    """Test post-payment onboarding stays public and contributor-friendly."""

    def test_success_output_points_to_public_audit_path(self, capsys):
        show_post_payment_experience(
            tx_id="tx_demo_123",
            tx_hash="0xabc123",
            amount=12.5,
            merchant="example.com",
            chain="base_sepolia",
        )

        captured = capsys.readouterr()
        assert "sardis ledger list" in captured.out
        assert "https://sardis.sh/docs" in captured.out
        assert "https://app.sardis.sh" not in captured.out
        assert ("Open " + "dashboard") not in captured.out
