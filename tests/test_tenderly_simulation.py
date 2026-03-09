"""Tests for Tenderly simulation integration."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_chain.simulation import (
    SimulationOutput,
    SimulationResult,
    SimulationRouter,
    TenderlySimulator,
    TransactionSimulator,
)

# ── TenderlySimulator ────────────────────────────────────────────────────


class TestTenderlySimulator:
    @pytest.fixture
    def simulator(self):
        return TenderlySimulator(
            account_slug="sardis",
            project_slug="sardis-prod",
            api_key="test-api-key",
        )

    def test_get_chain_id(self):
        assert TenderlySimulator.get_chain_id("base") == 8453
        assert TenderlySimulator.get_chain_id("base_sepolia") == 84532
        assert TenderlySimulator.get_chain_id("ethereum") == 1
        assert TenderlySimulator.get_chain_id("polygon") == 137
        assert TenderlySimulator.get_chain_id("arbitrum") == 42161
        assert TenderlySimulator.get_chain_id("optimism") == 10

    def test_get_chain_id_unknown(self):
        with pytest.raises(ValueError, match="Unknown chain"):
            TenderlySimulator.get_chain_id("unknown_chain")

    @pytest.mark.asyncio
    async def test_simulate_success(self, simulator):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transaction": {
                "status": True,
                "gas_used": 21000,
                "output": "0x",
                "logs": [],
            },
            "simulation": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await simulator.simulate(
                tx={"from": "0x1234", "to": "0x5678", "data": "0x"},
                chain_id=8453,
            )

        assert result.result == SimulationResult.SUCCESS
        assert result.gas_used == 21000

    @pytest.mark.asyncio
    async def test_simulate_revert(self, simulator):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transaction": {
                "status": False,
                "gas_used": 50000,
                "error_message": "execution reverted",
                "error_info": {"error_message": "Insufficient allowance"},
            },
            "simulation": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await simulator.simulate(
                tx={"from": "0x1234", "to": "0x5678", "data": "0x"},
                chain_id=8453,
            )

        assert result.result == SimulationResult.REVERTED
        assert result.revert_reason == "Insufficient allowance"

    @pytest.mark.asyncio
    async def test_simulate_timeout(self, simulator):
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await simulator.simulate(
                tx={"to": "0x5678", "data": "0x"},
                chain_id=8453,
            )

        assert result.result == SimulationResult.TIMEOUT

    @pytest.mark.asyncio
    async def test_simulate_api_error(self, simulator):
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server Error", request=MagicMock(), response=mock_response
                )
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await simulator.simulate(
                tx={"to": "0x5678", "data": "0x"},
                chain_id=8453,
            )

        assert result.result == SimulationResult.ERROR


# ── SimulationRouter ─────────────────────────────────────────────────────


class TestSimulationRouter:
    @pytest.mark.asyncio
    async def test_routes_to_tenderly_when_available(self):
        tenderly = AsyncMock(spec=TenderlySimulator)
        tenderly.simulate = AsyncMock(
            return_value=SimulationOutput(result=SimulationResult.SUCCESS, gas_used=50000)
        )
        router = SimulationRouter(tenderly=tenderly)

        result = await router.simulate(
            tx={"to": "0x1234", "data": "0x"},
            chain="base",
        )

        assert result.result == SimulationResult.SUCCESS
        assert result.gas_used == 50000
        tenderly.simulate.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_local_on_tenderly_error(self):
        tenderly = AsyncMock(spec=TenderlySimulator)
        tenderly.simulate = AsyncMock(
            return_value=SimulationOutput(
                result=SimulationResult.ERROR,
                error_message="API key invalid",
            )
        )

        rpc = AsyncMock()
        rpc.eth_call = AsyncMock(return_value="0x")

        local = AsyncMock(spec=TransactionSimulator)
        local.simulate = AsyncMock(
            return_value=SimulationOutput(result=SimulationResult.SUCCESS)
        )

        router = SimulationRouter(tenderly=tenderly, local=local)

        result = await router.simulate(
            tx={"to": "0x1234", "data": "0x"},
            chain="base",
            rpc_client=rpc,
        )

        assert result.result == SimulationResult.SUCCESS
        local.simulate.assert_called_once()

    @pytest.mark.asyncio
    async def test_local_only_when_no_tenderly(self):
        local = AsyncMock(spec=TransactionSimulator)
        local.simulate = AsyncMock(
            return_value=SimulationOutput(result=SimulationResult.SUCCESS)
        )

        router = SimulationRouter(tenderly=None, local=local)
        rpc = AsyncMock()

        result = await router.simulate(
            tx={"to": "0x1234", "data": "0x"},
            chain="base",
            rpc_client=rpc,
        )

        assert result.result == SimulationResult.SUCCESS
        local.simulate.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_when_no_backend_available(self):
        router = SimulationRouter(tenderly=None)

        result = await router.simulate(
            tx={"to": "0x1234", "data": "0x"},
            chain="base",
        )

        assert result.result == SimulationResult.ERROR
        assert "No simulation backend" in result.error_message

    def test_has_tenderly_property(self):
        router_with = SimulationRouter(tenderly=MagicMock())
        router_without = SimulationRouter(tenderly=None)

        assert router_with.has_tenderly is True
        assert router_without.has_tenderly is False

    def test_from_settings_with_tenderly(self):
        settings = MagicMock()
        settings.tenderly_api_key = "key123"
        settings.tenderly_account_slug = "sardis"
        settings.tenderly_project_slug = "prod"

        router = SimulationRouter.from_settings(settings)
        assert router.has_tenderly is True

    def test_from_settings_without_tenderly(self):
        settings = MagicMock()
        settings.tenderly_api_key = ""
        settings.tenderly_account_slug = ""
        settings.tenderly_project_slug = ""

        router = SimulationRouter.from_settings(settings)
        assert router.has_tenderly is False
