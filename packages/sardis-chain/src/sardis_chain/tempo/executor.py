"""Tempo chain executor — type 0x76 batch transactions.

Tempo's native transaction type 0x76 (EIP-2718) supports:
- Atomic batch calls: [{to, value, data}, ...] in a single tx
- 2D nonces for parallel submission
- Dual signatures: sender (0x76) + fee payer (0x78)
- Optional feeToken field for stablecoin gas
- No Multicall contracts needed — protocol-native

Network details:
  Mainnet: chain_id=4217, rpc=https://rpc.tempo.xyz
  Testnet: chain_id=42431, rpc=https://rpc.moderato.tempo.xyz
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger("sardis.chain.tempo")

# System contract addresses
ACCOUNT_KEYCHAIN = "0xAAAAAAAA00000000000000000000000000000000"
STABLECOIN_DEX = "0xdec0000000000000000000000000000000000000"
FEE_MANAGER = "0xfeec000000000000000000000000000000000000"
PATH_USD = "0x20c0000000000000000000000000000000000000"
USDC_E_BRIDGED = "0x20C000000000000000000000b9537d11c60E8b50"

# Chain configs
TEMPO_MAINNET = {
    "chain_id": 4217,
    "rpc": "https://rpc.tempo.xyz",
    "explorer": "https://explore.mainnet.tempo.xyz",
    "name": "Tempo Presto",
}
TEMPO_TESTNET = {
    "chain_id": 42431,
    "rpc": "https://rpc.moderato.tempo.xyz",
    "explorer": "https://explore.tempo.xyz",
    "name": "Tempo Moderato",
}


@dataclass
class BatchCall:
    """A single call within a type 0x76 batch transaction."""
    to: str
    value: int = 0
    data: bytes = field(default_factory=bytes)


@dataclass
class BatchTransaction:
    """A Tempo type 0x76 batch transaction."""
    calls: list[BatchCall] = field(default_factory=list)
    fee_token: str | None = None  # TIP-20 token address for gas
    nonce_key: int = 0  # 2D nonce key (for parallel submission)
    nonce_seq: int = 0  # 2D nonce sequence
    chain_id: int = 4217

    @property
    def call_count(self) -> int:
        return len(self.calls)


@dataclass
class TempoReceipt:
    """Receipt from a Tempo transaction."""
    tx_hash: str
    block_number: int
    status: bool  # True = success
    gas_used: int = 0
    fee_paid: Decimal = field(default_factory=lambda: Decimal("0"))
    fee_token: str | None = None
    calls_results: list[bool] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TempoExecutor:
    """Executes transactions on Tempo using type 0x76 batch transactions.

    All agent transactions are batched and gas-sponsored by Sardis.
    Agents never need gas tokens on Tempo.
    """

    def __init__(
        self,
        rpc_url: str | None = None,
        chain_id: int = 4217,
        signer=None,
        fee_payer=None,
    ) -> None:
        config = TEMPO_MAINNET if chain_id == 4217 else TEMPO_TESTNET
        self._rpc_url = rpc_url or config["rpc"]
        self._chain_id = chain_id
        self._signer = signer
        self._fee_payer = fee_payer

    async def execute_transfer(
        self,
        token_address: str,
        to: str,
        amount: int,
        memo: bytes | None = None,
    ) -> TempoReceipt:
        """Execute a single TIP-20 transfer with optional memo.

        Uses transferWithMemo if memo is provided (32-byte field
        for mandate_id / invoice_id linking).
        """
        if memo:
            # TIP-20 transferWithMemo(address,uint256,bytes32)
            data = self._encode_transfer_with_memo(to, amount, memo)
        else:
            # Standard ERC-20 transfer(address,uint256)
            data = self._encode_transfer(to, amount)

        batch = BatchTransaction(
            calls=[BatchCall(to=token_address, data=data)],
            fee_token=token_address,  # Pay gas in same token
            chain_id=self._chain_id,
        )

        return await self._submit_batch(batch)

    async def execute_batch_transfers(
        self,
        transfers: list[dict[str, Any]],
        fee_token: str | None = None,
    ) -> TempoReceipt:
        """Execute multiple transfers atomically in a single type 0x76 tx.

        Each transfer dict: {token, to, amount, memo?}
        """
        calls = []
        for t in transfers:
            memo = t.get("memo")
            if memo:
                data = self._encode_transfer_with_memo(t["to"], t["amount"], memo)
            else:
                data = self._encode_transfer(t["to"], t["amount"])
            calls.append(BatchCall(to=t["token"], data=data))

        batch = BatchTransaction(
            calls=calls,
            fee_token=fee_token or (transfers[0]["token"] if transfers else None),
            chain_id=self._chain_id,
        )

        return await self._submit_batch(batch)

    async def execute_dex_swap(
        self,
        from_token: str,
        to_token: str,
        amount: int,
        min_output: int,
    ) -> TempoReceipt:
        """Execute a swap on Tempo's enshrined DEX.

        The DEX at 0xdec0... is a native orderbook (not AMM).
        """
        # Approve DEX to spend tokens + execute swap in one batch
        approve_data = self._encode_approve(STABLECOIN_DEX, amount)
        swap_data = self._encode_dex_swap(from_token, to_token, amount, min_output)

        batch = BatchTransaction(
            calls=[
                BatchCall(to=from_token, data=approve_data),
                BatchCall(to=STABLECOIN_DEX, data=swap_data),
            ],
            fee_token=from_token,
            chain_id=self._chain_id,
        )

        return await self._submit_batch(batch)

    async def _submit_batch(self, batch: BatchTransaction) -> TempoReceipt:
        """Submit a type 0x76 batch transaction to Tempo."""
        import httpx

        # Build the type 0x76 transaction envelope
        tx_data = {
            "type": "0x76",
            "chainId": hex(batch.chain_id),
            "calls": [
                {
                    "to": call.to,
                    "value": hex(call.value),
                    "data": "0x" + call.data.hex() if call.data else "0x",
                }
                for call in batch.calls
            ],
        }
        if batch.fee_token:
            tx_data["feeToken"] = batch.fee_token

        # Sign with sender key (0x76 signature)
        if self._signer:
            tx_data = await self._signer.sign_batch(tx_data)

        # Add fee payer signature (0x78 magic byte) if available
        if self._fee_payer:
            tx_data = await self._fee_payer.co_sign(tx_data)

        # Submit via JSON-RPC
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self._rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_sendTransaction",
                    "params": [tx_data],
                    "id": 1,
                },
            )
            result = resp.json()

        if "error" in result:
            logger.error("Tempo tx failed: %s", result["error"])
            return TempoReceipt(
                tx_hash="0x" + "0" * 64,
                block_number=0,
                status=False,
            )

        tx_hash = result.get("result", "")
        logger.info("Tempo batch tx submitted: %s (%d calls)", tx_hash, batch.call_count)

        # Wait for receipt
        receipt = await self._wait_for_receipt(tx_hash)
        return receipt

    async def _wait_for_receipt(self, tx_hash: str) -> TempoReceipt:
        """Poll for transaction receipt (Tempo has ~0.5s finality)."""
        import asyncio
        import httpx

        for _ in range(20):  # 10 seconds max
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_getTransactionReceipt",
                        "params": [tx_hash],
                        "id": 1,
                    },
                )
                result = resp.json()

            receipt = result.get("result")
            if receipt:
                return TempoReceipt(
                    tx_hash=tx_hash,
                    block_number=int(receipt.get("blockNumber", "0x0"), 16),
                    status=receipt.get("status") == "0x1",
                    gas_used=int(receipt.get("gasUsed", "0x0"), 16),
                )

            await asyncio.sleep(0.5)

        logger.warning("Timeout waiting for receipt: %s", tx_hash)
        return TempoReceipt(tx_hash=tx_hash, block_number=0, status=False)

    # -- ABI encoding helpers --

    @staticmethod
    def _encode_transfer(to: str, amount: int) -> bytes:
        """Encode ERC-20 transfer(address,uint256)."""
        selector = bytes.fromhex("a9059cbb")
        addr = bytes.fromhex(to[2:].zfill(64))
        amt = amount.to_bytes(32, "big")
        return selector + addr + amt

    @staticmethod
    def _encode_transfer_with_memo(to: str, amount: int, memo: bytes) -> bytes:
        """Encode TIP-20 transferWithMemo(address,uint256,bytes32)."""
        selector = bytes.fromhex("b3e5ff47")  # transferWithMemo selector
        addr = bytes.fromhex(to[2:].zfill(64))
        amt = amount.to_bytes(32, "big")
        memo_padded = memo.ljust(32, b"\x00")[:32]
        return selector + addr + amt + memo_padded

    @staticmethod
    def _encode_approve(spender: str, amount: int) -> bytes:
        """Encode ERC-20 approve(address,uint256)."""
        selector = bytes.fromhex("095ea7b3")
        addr = bytes.fromhex(spender[2:].zfill(64))
        amt = amount.to_bytes(32, "big")
        return selector + addr + amt

    @staticmethod
    def _encode_dex_swap(
        from_token: str, to_token: str, amount: int, min_output: int
    ) -> bytes:
        """Encode DEX swap call."""
        # Simplified — actual ABI depends on Tempo DEX precompile interface
        selector = bytes.fromhex("38ed1739")  # swap selector
        from_addr = bytes.fromhex(from_token[2:].zfill(64))
        to_addr = bytes.fromhex(to_token[2:].zfill(64))
        amt = amount.to_bytes(32, "big")
        min_out = min_output.to_bytes(32, "big")
        return selector + from_addr + to_addr + amt + min_out
