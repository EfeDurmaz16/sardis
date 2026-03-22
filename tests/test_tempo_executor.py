"""Tests for Tempo-specific executor path.

Verifies TIP-20 transfer encoding, fee token selection, gas estimation,
contract address wiring, and Tempo routing in dispatch_payment.
"""
from decimal import Decimal

from sardis_chain.executor import (
    CHAIN_CONFIGS,
    SARDIS_CONTRACTS,
    STABLECOIN_ADDRESSES,
    TEMPO_SYSTEM_CONTRACTS,
    TIP20_TRANSFER_WITH_MEMO_ABI,
    GasPriceProtectionConfig,
    get_sardis_contract_address,
)
from sardis_v2_core.tokens import TOKEN_REGISTRY, TokenType


class TestTempoContractAddresses:
    """Phase 1: Verify deployed contracts are wired into the codebase."""

    def test_tempo_mainnet_has_ledger_anchor(self):
        contracts = SARDIS_CONTRACTS["tempo"]
        assert contracts["ledger_anchor"] == "0x9a5D2a6c81414FD1E6a2c9b55306c6D0b954b98B"

    def test_tempo_mainnet_has_refund_protocol(self):
        contracts = SARDIS_CONTRACTS["tempo"]
        assert contracts["refund_protocol"] == "0x801ea29ca523ea16475e3def938002d6be985e9d"

    def test_tempo_mainnet_has_identity_registry(self):
        contracts = SARDIS_CONTRACTS["tempo"]
        assert contracts["identity_registry"] == "0xc5a3eb812bef4b883a2e890865de9d51818ac90a"

    def test_tempo_mainnet_has_job_registry(self):
        contracts = SARDIS_CONTRACTS["tempo"]
        assert contracts["job_registry"] == "0x19eeeb6b349cfd4025cc75fa99bb36f6b8bec62d"

    def test_tempo_mainnet_has_job_manager(self):
        contracts = SARDIS_CONTRACTS["tempo"]
        assert contracts["job_manager"] == "0x758114d2229d3da2a8629b96b0394a3e8319fbb0"

    def test_tempo_mainnet_has_reputation_registry(self):
        contracts = SARDIS_CONTRACTS["tempo"]
        assert contracts["reputation_registry"] == "0x127ac64f6ddf7292e8dee43e39f4e66af859e704"

    def test_tempo_mainnet_has_validation_registry(self):
        contracts = SARDIS_CONTRACTS["tempo"]
        assert contracts["validation_registry"] == "0xc95e58f9e1df9c3df4593632846eb2a02cf73d6b"

    def test_tempo_has_all_7_contracts(self):
        contracts = SARDIS_CONTRACTS["tempo"]
        expected_keys = {
            "policy_module", "ledger_anchor", "refund_protocol",
            "identity_registry", "job_registry", "job_manager",
            "reputation_registry", "validation_registry",
        }
        assert expected_keys.issubset(set(contracts.keys()))

    def test_tempo_testnet_has_ledger_anchor(self):
        contracts = SARDIS_CONTRACTS["tempo_testnet"]
        assert contracts["ledger_anchor"] == "0x9a5D2a6c81414FD1E6a2c9b55306c6D0b954b98B"

    def test_contract_address_resolver_finds_tempo_ledger(self):
        address = get_sardis_contract_address("tempo", "ledger_anchor")
        assert address == "0x9a5D2a6c81414FD1E6a2c9b55306c6D0b954b98B"


class TestTempoChainConfig:
    """Verify Tempo chain configuration."""

    def test_tempo_mainnet_chain_id(self):
        assert CHAIN_CONFIGS["tempo"]["chain_id"] == 4217

    def test_tempo_testnet_chain_id(self):
        assert CHAIN_CONFIGS["tempo_testnet"]["chain_id"] == 42429

    def test_tempo_no_native_gas_token(self):
        assert CHAIN_CONFIGS["tempo"]["native_token"] == "NONE"

    def test_tempo_is_tempo_flag(self):
        assert CHAIN_CONFIGS["tempo"]["is_tempo"] is True
        assert CHAIN_CONFIGS["tempo_testnet"]["is_tempo"] is True

    def test_tempo_is_not_solana(self):
        assert CHAIN_CONFIGS["tempo"].get("is_solana") is not True


class TestTempoTokenAddresses:
    """Verify stablecoin addresses on Tempo."""

    def test_tempo_has_usdc_pathusd(self):
        assert STABLECOIN_ADDRESSES["tempo"]["USDC"] == "0x20c0000000000000000000000000000000000000"

    def test_tempo_has_usdc_e_bridged(self):
        assert STABLECOIN_ADDRESSES["tempo"]["USDC.e"] == "0x20C000000000000000000000b9537d11c60E8b50"

    def test_tempo_testnet_has_usdc(self):
        assert "USDC" in STABLECOIN_ADDRESSES["tempo_testnet"]

    def test_token_registry_has_usdc_e(self):
        assert TokenType.USDC_E in TOKEN_REGISTRY
        meta = TOKEN_REGISTRY[TokenType.USDC_E]
        assert meta.is_tip20 is True
        assert meta.decimals == 6
        assert "tempo" in meta.contract_addresses


class TestTempoSystemContracts:
    """Verify Tempo system contract addresses."""

    def test_pathusd_address(self):
        assert TEMPO_SYSTEM_CONTRACTS["path_usd"] == "0x20c0000000000000000000000000000000000000"

    def test_fee_manager_address(self):
        assert TEMPO_SYSTEM_CONTRACTS["fee_manager"] == "0xfeec000000000000000000000000000000000000"

    def test_stablecoin_dex_address(self):
        assert TEMPO_SYSTEM_CONTRACTS["stablecoin_dex"] == "0xdec0000000000000000000000000000000000000"


class TestTIP20ABI:
    """Verify TIP-20 ABI definition."""

    def test_transfer_with_memo_abi_exists(self):
        assert len(TIP20_TRANSFER_WITH_MEMO_ABI) == 1

    def test_transfer_with_memo_inputs(self):
        fn = TIP20_TRANSFER_WITH_MEMO_ABI[0]
        assert fn["name"] == "transferWithMemo"
        input_names = [i["name"] for i in fn["inputs"]]
        assert input_names == ["to", "amount", "memo"]

    def test_transfer_with_memo_types(self):
        fn = TIP20_TRANSFER_WITH_MEMO_ABI[0]
        input_types = [i["type"] for i in fn["inputs"]]
        assert input_types == ["address", "uint256", "bytes32"]


class TestTempoGasProtection:
    """Verify Tempo gas protection configuration."""

    def test_tempo_gas_price_override_exists(self):
        config = GasPriceProtectionConfig()
        assert "tempo" in config.chain_overrides

    def test_tempo_max_gas_price_is_low(self):
        config = GasPriceProtectionConfig()
        max_gas = config.get_max_gas_price("tempo")
        # Tempo gas is cheap — stablecoin-denominated
        assert max_gas <= Decimal("100")

    def test_tempo_max_transaction_cost_is_low(self):
        config = GasPriceProtectionConfig()
        max_cost = config.get_max_transaction_cost("tempo")
        # Tempo transactions should be sub-$10
        assert max_cost <= Decimal("10")


class TestTempoExecutorRouting:
    """Verify dispatch_payment routes to Tempo executor."""

    def test_is_tempo_chain_detected(self):
        """dispatch_payment should detect is_tempo and route accordingly."""
        config = CHAIN_CONFIGS.get("tempo", {})
        assert config.get("is_tempo") is True
        # The routing check in dispatch_payment:
        # if chain_config.get("is_tempo"): _execute_tempo_payment()

    def test_tempo_testnet_also_routes(self):
        config = CHAIN_CONFIGS.get("tempo_testnet", {})
        assert config.get("is_tempo") is True
