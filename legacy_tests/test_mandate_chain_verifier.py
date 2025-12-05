from sardis_protocol.verifier import MandateVerifier
from sardis_v2_core import SardisSettings
from tests.ap2_helpers import build_signed_bundle


def _settings() -> SardisSettings:
    return SardisSettings(
        allowed_domains=["merchant.example"],
        chains=[
            {
                "name": "base",
                "rpc_url": "https://base.example",
                "chain_id": 84532,
                "stablecoins": ["USDC"],
                "settlement_vault": "0x0000000000000000000000000000000000000000",
            }
        ],
        mpc={"name": "turnkey", "api_base": "https://turnkey.example", "credential_id": "cred"},
    )


def test_verify_chain_success():
    verifier = MandateVerifier(settings=_settings())
    bundle = build_signed_bundle()
    result = verifier.verify_chain(bundle)
    assert result.accepted
    assert result.chain is not None
    assert result.chain.payment.mandate_id.startswith("payment-")


def test_verify_chain_subject_mismatch_fails():
    verifier = MandateVerifier(settings=_settings())
    bundle = build_signed_bundle()
    bundle.cart["subject"] = "someone-else"
    result = verifier.verify_chain(bundle)
    assert not result.accepted
    assert result.reason == "subject_mismatch"
