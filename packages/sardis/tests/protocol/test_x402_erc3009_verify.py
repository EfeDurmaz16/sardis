"""EIP-3009 TransferWithAuthorization signature recovery + verification tests.

These prove the real fail-closed guarantee for x402: a payment proof is only
accepted when a genuine EIP-712 signature recovers to the claimed payer and the
authorization binds to the right token contract / chain.
"""
from __future__ import annotations

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data

from sardis.protocol.x402_erc3009 import (
    TRANSFER_WITH_AUTHORIZATION_TYPE,
    ERC3009Authorization,
    ERC3009VerificationError,
    recover_transfer_authorization_signer,
    resolve_eip712_domain,
    verify_transfer_authorization,
)

PAYEE = "0x" + "a" * 40
NONCE = "0x" + "11" * 32


def _sign(acct, *, network="base", to=PAYEE, value=1000000, valid_after=0, valid_before=9999999999, nonce=NONCE):
    domain = resolve_eip712_domain(network)
    message = {
        "from": acct.address,
        "to": to,
        "value": value,
        "validAfter": valid_after,
        "validBefore": valid_before,
        "nonce": bytes.fromhex(nonce[2:]),
    }
    signable = encode_typed_data(
        domain, {"TransferWithAuthorization": TRANSFER_WITH_AUTHORIZATION_TYPE}, message
    )
    signed = acct.sign_message(signable)
    auth = ERC3009Authorization(
        from_address=acct.address,
        to_address=to,
        value=value,
        valid_after=valid_after,
        valid_before=valid_before,
        nonce=nonce,
    )
    return auth, "0x" + signed.signature.hex()


def test_recover_matches_signer():
    acct = Account.create()
    auth, sig = _sign(acct)
    recovered = recover_transfer_authorization_signer(auth, sig, network="base")
    assert recovered.lower() == acct.address.lower()


def test_verify_good_signature_accepted():
    acct = Account.create()
    auth, sig = _sign(acct)
    ok, reason = verify_transfer_authorization(
        auth, sig, network="base", expected_payer=acct.address
    )
    assert ok is True
    assert reason is None


def test_verify_forged_signature_rejected():
    """Authorization from victim, signature from attacker → rejected."""
    victim = Account.create()
    attacker = Account.create()
    victim_auth, _ = _sign(victim)
    _, attacker_sig = _sign(attacker)
    ok, reason = verify_transfer_authorization(
        victim_auth, attacker_sig, network="base", expected_payer=victim.address
    )
    assert ok is False
    assert reason == "signer_mismatch_authorization_from"


def test_verify_payer_mismatch_rejected():
    """Genuine self-consistent signature but wrong claimed payer → rejected."""
    acct = Account.create()
    other = Account.create()
    auth, sig = _sign(acct)
    ok, reason = verify_transfer_authorization(
        auth, sig, network="base", expected_payer=other.address
    )
    assert ok is False
    assert reason == "signer_mismatch_payer_address"


def test_verify_wrong_network_domain_rejected():
    """Sig made for base but verified against base_sepolia domain → signer differs."""
    acct = Account.create()
    auth, sig = _sign(acct, network="base")
    ok, reason = verify_transfer_authorization(
        auth, sig, network="base_sepolia", expected_payer=acct.address
    )
    # Different verifyingContract/chainId → recovered signer won't match.
    assert ok is False


def test_verify_expired_authorization_rejected():
    acct = Account.create()
    auth, sig = _sign(acct, valid_before=100)
    ok, reason = verify_transfer_authorization(
        auth, sig, network="base", expected_payer=acct.address, now=200
    )
    assert ok is False
    assert reason == "authorization_expired"


def test_verify_not_yet_valid_rejected():
    acct = Account.create()
    auth, sig = _sign(acct, valid_after=500, valid_before=1000)
    ok, reason = verify_transfer_authorization(
        auth, sig, network="base", expected_payer=acct.address, now=100
    )
    assert ok is False
    assert reason == "authorization_not_yet_valid"


def test_bad_signature_length_rejected():
    acct = Account.create()
    auth, _ = _sign(acct)
    ok, reason = verify_transfer_authorization(
        auth, "0xdeadbeef", network="base", expected_payer=acct.address
    )
    assert ok is False
    assert "signature_bad_length" in reason


def test_unsupported_network_raises():
    with pytest.raises(ERC3009VerificationError):
        resolve_eip712_domain("dogecoin")
