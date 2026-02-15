"""UserOperation primitives for ERC-4337."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from web3 import Web3


def zero_hex() -> str:
    return "0x"


def _to_hex_int(value: int) -> str:
    return hex(max(0, int(value)))


@dataclass
class UserOperation:
    sender: str
    nonce: int
    init_code: str
    call_data: str
    call_gas_limit: int
    verification_gas_limit: int
    pre_verification_gas: int
    max_fee_per_gas: int
    max_priority_fee_per_gas: int
    paymaster_and_data: str
    signature: str

    @staticmethod
    def encode_execute(to: str, value: int, data: bytes) -> str:
        selector = Web3.keccak(text="execute(address,uint256,bytes)")[:4]
        from eth_abi import encode

        encoded = encode(["address", "uint256", "bytes"], [to, value, data])
        return "0x" + (selector + encoded).hex()

    def to_rpc(self) -> dict[str, Any]:
        return {
            "sender": self.sender,
            "nonce": _to_hex_int(self.nonce),
            "initCode": self.init_code,
            "callData": self.call_data,
            "callGasLimit": _to_hex_int(self.call_gas_limit),
            "verificationGasLimit": _to_hex_int(self.verification_gas_limit),
            "preVerificationGas": _to_hex_int(self.pre_verification_gas),
            "maxFeePerGas": _to_hex_int(self.max_fee_per_gas),
            "maxPriorityFeePerGas": _to_hex_int(self.max_priority_fee_per_gas),
            "paymasterAndData": self.paymaster_and_data,
            "signature": self.signature,
        }
