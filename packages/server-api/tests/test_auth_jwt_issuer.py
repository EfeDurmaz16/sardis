from __future__ import annotations

import time
from types import SimpleNamespace

import jwt as pyjwt

from sardis_server.routes.accounts import auth


def test_internal_jwt_tokens_include_issuer_and_audience():
    token = auth.create_jwt_token(
        {
            "sub": "user_1",
            "role": "user",
            "jti": "jti_1",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
    )

    payload = auth.verify_jwt_token(token)

    assert payload is not None
    assert payload["iss"] == auth.INTERNAL_JWT_ISSUER
    assert payload["aud"] == auth.INTERNAL_JWT_AUDIENCE


def test_internal_jwt_rejects_wrong_issuer():
    token = pyjwt.encode(
        {
            "sub": "user_1",
            "role": "user",
            "jti": "jti_2",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": "https://evil.example",
            "aud": auth.INTERNAL_JWT_AUDIENCE,
        },
        auth.JWT_SECRET,
        algorithm=auth.JWT_ALGORITHM,
    )

    assert auth.verify_jwt_token(token) is None


def test_better_auth_jwks_decode_is_bound_to_issuer(monkeypatch):
    captured: dict = {}

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, token: str):
            assert token == "jwks-token"
            return SimpleNamespace(key="public-key")

    def fake_decode(token: str, key: str, **kwargs):
        if kwargs["algorithms"] == [auth.JWT_ALGORITHM]:
            raise pyjwt.InvalidTokenError("not an internal token")
        captured.update(kwargs)
        return {
            "sub": "user_1",
            "exp": int(time.time()) + 3600,
            "iss": "https://dashboard.sardis.sh",
            "aud": "sardis-api",
        }

    monkeypatch.setattr(auth, "_jwks_client", FakeJWKSClient())
    monkeypatch.setattr(auth, "BETTER_AUTH_ISSUER", "https://dashboard.sardis.sh")
    monkeypatch.setattr(auth, "BETTER_AUTH_AUDIENCE", "sardis-api")
    monkeypatch.setattr(auth.pyjwt, "decode", fake_decode)

    payload = auth.verify_jwt_token("jwks-token")

    assert payload is not None
    assert captured["issuer"] == "https://dashboard.sardis.sh"
    assert captured["audience"] == "sardis-api"
    assert "iss" in captured["options"]["require"]
