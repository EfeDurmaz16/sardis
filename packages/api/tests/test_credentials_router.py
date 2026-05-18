from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routes.authority.credentials import router


class _Credential:
    def __init__(self, credential_id: str) -> None:
        self.credential_id = credential_id


class _CredentialStore:
    def __init__(self, credential: _Credential) -> None:
        self._credential = credential
        self.rotate_calls: list[tuple[str, bytes]] = []

    async def get(self, credential_id: str) -> _Credential | None:
        if credential_id != self._credential.credential_id:
            return None
        return self._credential

    async def rotate(self, credential_id: str, new_token: bytes) -> _Credential:
        self.rotate_calls.append((credential_id, new_token))
        return self._credential


def _make_app(
    *,
    credential_store: _CredentialStore,
    delegated_adapter: object | None = None,
) -> FastAPI:
    app = FastAPI()
    app.state.credential_store = credential_store
    app.state.consent_store = SimpleNamespace()
    app.state.delegated_adapter = delegated_adapter
    app.state.credential_encryption = object()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_test_001",
        scopes=["*"],
    )
    app.include_router(router)
    return app


def test_rotate_credential_returns_truthful_failure_when_provider_rotation_is_unavailable() -> None:
    store = _CredentialStore(_Credential("cred_123"))
    app = _make_app(credential_store=store, delegated_adapter=object())

    with TestClient(app) as client:
        response = client.post("/api/v2/credentials/cred_123/rotate")

    assert response.status_code == 501, response.text
    assert "does not implement real token rotation" in response.json()["detail"]
    assert store.rotate_calls == []


def test_rotate_credential_persists_real_provider_token() -> None:
    store = _CredentialStore(_Credential("cred_123"))

    class _RotatingAdapter:
        async def rotate_credential(self, credential: _Credential, *, encryption: object | None = None) -> bytes:
            assert credential.credential_id == "cred_123"
            assert encryption is not None
            return b"real_rotated_token"

    app = _make_app(credential_store=store, delegated_adapter=_RotatingAdapter())

    with TestClient(app) as client:
        response = client.post("/api/v2/credentials/cred_123/rotate")

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "rotated", "credential_id": "cred_123"}
    assert store.rotate_calls == [("cred_123", b"real_rotated_token")]
