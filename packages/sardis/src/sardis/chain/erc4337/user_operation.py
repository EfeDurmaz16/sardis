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
        """Encode SimpleAccount execute() calldata (legacy)."""
        selector = Web3.keccak(text="execute(address,uint256,bytes)")[:4]
        from eth_abi import encode

        encoded = encode(["address", "uint256", "bytes"], [to, value, data])
        return "0x" + (selector + encoded).hex()

    @staticmethod
    def encode_safe_execute(to: str, value: int, data: bytes) -> str:
        """Encode Safe4337Module executeUserOp() calldata.

        Safe uses executeUserOp(address,uint256,bytes,uint8) where the
        last param is the operation type (0=Call, 1=DelegateCall).
        """
        selector = Web3.keccak(text="executeUserOp(address,uint256,bytes,uint8)")[:4]
        from eth_abi import encode

        encoded = encode(
            ["address", "uint256", "bytes", "uint8"],
            [to, value, data, 0],  # 0 = Call
        )
        return "0x" + (selector + encoded).hex()

    @staticmethod
    def build_safe_init_code(
        owner: str,
        policy_module: str,
        salt_nonce: int,
    ) -> str:
        """Build initCode for first UserOp that deploys a Safe proxy.

        Delegates to safe_account module for the actual encoding.
        """
        from sardis_chain.safe_account import build_safe_init_code
        return build_safe_init_code(owner, policy_module, salt_nonce)

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
