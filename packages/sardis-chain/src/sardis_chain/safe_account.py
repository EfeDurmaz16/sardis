"""Safe Smart Account helpers for proxy deployment and address prediction.

Uses Safe's canonical infrastructure (already deployed on all EVM chains):
- SafeProxyFactory for CREATE2 proxy deployment
- Safe singleton (v1.4.1) as implementation
- Safe4337Module for ERC-4337 compatibility
- MultiSend for batched operations

References:
- https://github.com/safe-global/safe-smart-account
- https://github.com/safe-global/safe-modules
"""

from __future__ import annotations

from web3 import Web3
from eth_abi import encode


# ============ Canonical Safe Addresses ============
# Same on all EVM chains (CREATE2 deterministic deployment)

SAFE_ADDRESSES = {
    "proxy_factory": "0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2",
    "safe_singleton": "0x41675C099F32341bf84BFc5382aF534df5C7461a",  # v1.4.1
    "safe_4337_module": "0x75cf11467937ce3F2f357CE24ffc3DBF8fD5c226",
    "multi_send": "0x38869bf66a61cF6bDB996A6aE40D5853Fd43B526",
    "fallback_handler": "0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99",
}


def _address_to_bytes32(addr: str) -> bytes:
    """Pad an address to 32 bytes."""
    return bytes.fromhex(addr[2:].lower().zfill(64))


def _encode_safe_setup(
    owner: str,
    policy_module: str,
    fallback_handler: str | None = None,
) -> bytes:
    """Encode Safe.setup() calldata for a single-owner Safe with policy module.

    Safe.setup(
        address[] _owners,
        uint256 _threshold,
        address to,               # delegatecall target for setup
        bytes data,               # delegatecall data for setup
        address fallbackHandler,
        address paymentToken,
        uint256 payment,
        address paymentReceiver
    )
    """
    if fallback_handler is None:
        fallback_handler = SAFE_ADDRESSES["fallback_handler"]

    # Enable the policy module via delegatecall during setup
    # We call enableModule(address) on the Safe itself
    enable_module_data = Web3.keccak(text="enableModule(address)")[:4] + encode(
        ["address"], [Web3.to_checksum_address(policy_module)]
    )

    setup_selector = Web3.keccak(
        text="setup(address[],uint256,address,bytes,address,address,uint256,address)"
    )[:4]

    setup_params = encode(
        [
            "address[]",
            "uint256",
            "address",
            "bytes",
            "address",
            "address",
            "uint256",
            "address",
        ],
        [
            [Web3.to_checksum_address(owner)],  # owners
            1,  # threshold
            Web3.to_checksum_address(owner),  # to (delegatecall target - self for enableModule)
            enable_module_data,  # data
            Web3.to_checksum_address(fallback_handler),  # fallbackHandler
            "0x0000000000000000000000000000000000000000",  # paymentToken
            0,  # payment
            "0x0000000000000000000000000000000000000000",  # paymentReceiver
        ],
    )

    return setup_selector + setup_params


def predict_safe_address(
    owner: str,
    salt_nonce: int,
    policy_module: str,
    fallback_handler: str | None = None,
) -> str:
    """Predict the CREATE2 address of a Safe proxy before deployment.

    Uses the same algorithm as SafeProxyFactory.createProxyWithNonce():
    - salt = keccak256(keccak256(initializer) + saltNonce)
    - address = CREATE2(factory, salt, keccak256(proxyCreationCode + singleton))

    Args:
        owner: EOA address (Turnkey MPC signer)
        salt_nonce: Unique nonce for CREATE2 salt
        policy_module: SardisPolicyModule address on this chain
        fallback_handler: Optional fallback handler override

    Returns:
        Predicted Safe proxy address (checksummed)
    """
    initializer = _encode_safe_setup(owner, policy_module, fallback_handler)

    # Salt = keccak256(keccak256(initializer) + saltNonce)
    initializer_hash = Web3.keccak(initializer)
    salt = Web3.keccak(
        initializer_hash + encode(["uint256"], [salt_nonce])
    )

    # CREATE2: keccak256(0xff ++ factory ++ salt ++ keccak256(proxyCreationCode ++ singleton))
    #
    # The proxy creation code hash depends on the singleton address.
    # SafeProxyFactory internally does:
    #   keccak256(abi.encodePacked(proxyCreationCode, uint256(uint160(_singleton))))
    # We replicate this by hashing the SafeProxy bytecode + singleton param.
    singleton = SAFE_ADDRESSES["safe_singleton"]
    # SafeProxy deployment bytecode (canonical, from safe-smart-account v1.4.1)
    _PROXY_BYTECODE = (
        "608060405234801561001057600080fd5b50"
        "6040516101e63803806101e68339818101604052"
        "8101906100329190610054565b806000806101000a"
        "81548173ffffffffffffffffffffffffffffffff"
        "ffff021916908373ffffffffffffffffffffffffffffff"
        "ffffffffff16021790555050610097565b600081"
        "519050600073ffffffffffffffffffffffffffffffffffff"
        "ffff169050919050565b61014a806100a66000396000f3fe"
    )
    proxy_creation_code = bytes.fromhex(_PROXY_BYTECODE) + encode(
        ["uint256"], [int(singleton, 16)]
    )
    factory = SAFE_ADDRESSES["proxy_factory"]
    init_code_hash = Web3.keccak(proxy_creation_code)

    create2_input = (
        b"\xff"
        + bytes.fromhex(factory[2:])
        + salt
        + init_code_hash
    )
    address_hash = Web3.keccak(create2_input)
    predicted = "0x" + address_hash[-20:].hex()

    return Web3.to_checksum_address(predicted)


def build_safe_init_code(
    owner: str,
    policy_module: str,
    salt_nonce: int,
    fallback_handler: str | None = None,
) -> str:
    """Build initCode for the first ERC-4337 UserOp that deploys the Safe proxy.

    The initCode is: factory_address + createProxyWithNonce(singleton, initializer, saltNonce)

    Args:
        owner: EOA address (Turnkey MPC signer)
        policy_module: SardisPolicyModule address on this chain
        salt_nonce: CREATE2 salt nonce
        fallback_handler: Optional fallback handler override

    Returns:
        Hex-encoded initCode for UserOperation
    """
    initializer = _encode_safe_setup(owner, policy_module, fallback_handler)

    # createProxyWithNonce(address _singleton, bytes initializer, uint256 saltNonce)
    create_proxy_selector = Web3.keccak(
        text="createProxyWithNonce(address,bytes,uint256)"
    )[:4]
    create_proxy_params = encode(
        ["address", "bytes", "uint256"],
        [
            Web3.to_checksum_address(SAFE_ADDRESSES["safe_singleton"]),
            initializer,
            salt_nonce,
        ],
    )

    factory = SAFE_ADDRESSES["proxy_factory"]
    calldata = create_proxy_selector + create_proxy_params

    return factory + "0x" + calldata.hex()


def encode_safe_exec(to: str, value: int, data: bytes) -> str:
    """Encode Safe's execTransaction calldata for a single operation.

    This wraps a call through the Safe4337Module's executeUserOp interface.

    Args:
        to: Target contract address
        value: ETH value to send
        data: Calldata for the target

    Returns:
        Hex-encoded calldata for executeUserOp
    """
    # Safe4337Module.executeUserOp(address to, uint256 value, bytes data, uint8 operation)
    selector = Web3.keccak(text="executeUserOp(address,uint256,bytes,uint8)")[:4]
    params = encode(
        ["address", "uint256", "bytes", "uint8"],
        [Web3.to_checksum_address(to), value, data, 0],  # 0 = Call (not DelegateCall)
    )
    return "0x" + (selector + params).hex()
