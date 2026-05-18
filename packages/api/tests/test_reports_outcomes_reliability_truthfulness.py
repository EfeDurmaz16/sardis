from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers import outcomes, reliability, reports


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_test_001",
        scopes=["*"],
    )


def _reset_state() -> None:
    reports.set_report_generator(None)
    outcomes.set_outcome_tracker(None)
    reliability.set_provider_tracker(None)


def _build_reports_client() -> TestClient:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    app.include_router(reports.router)
    return TestClient(app)


def _build_outcomes_client() -> TestClient:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    app.include_router(outcomes.router)
    return TestClient(app)


def _build_reliability_client() -> TestClient:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    app.include_router(reliability.router)
    return TestClient(app)


def test_reports_require_persistent_backend_without_explicit_sandbox(monkeypatch) -> None:
    _reset_state()
    monkeypatch.delenv("SARDIS_REPORTS_SANDBOX", raising=False)

    with _build_reports_client() as client:
        response = client.post(
            "/reports/generate",
            json={
                "report_type": "monthly_spending",
                "date_from": date(2026, 1, 1).isoformat(),
                "date_to": date(2026, 1, 31).isoformat(),
                "format": "json",
            },
        )

    assert response.status_code == 501, response.text
    assert "SARDIS_REPORTS_SANDBOX=true" in response.json()["detail"]


def test_reports_allow_explicit_sandbox(monkeypatch) -> None:
    _reset_state()
    monkeypatch.setenv("SARDIS_REPORTS_SANDBOX", "true")

    with _build_reports_client() as client:
        response = client.post(
            "/reports/generate",
            json={
                "report_type": "monthly_spending",
                "date_from": date(2026, 1, 1).isoformat(),
                "date_to": date(2026, 1, 31).isoformat(),
                "format": "json",
            },
        )

    assert response.status_code == 200, response.text
    assert response.json()["report_type"] == "monthly_spending"


def test_outcomes_require_persistent_backend_without_explicit_sandbox(monkeypatch) -> None:
    _reset_state()
    monkeypatch.delenv("SARDIS_OUTCOMES_SANDBOX", raising=False)

    with _build_outcomes_client() as client:
        response = client.post(
            "/outcomes/outcome_test_123/resolve",
            json={"outcome_type": "completed", "data": {}},
        )

    assert response.status_code == 501, response.text
    assert "SARDIS_OUTCOMES_SANDBOX=true" in response.json()["detail"]


def test_reliability_requires_persistent_backend_without_explicit_sandbox(monkeypatch) -> None:
    _reset_state()
    monkeypatch.delenv("SARDIS_RELIABILITY_SANDBOX", raising=False)

    with _build_reliability_client() as client:
        response = client.get("/providers/provider_a/base")

    assert response.status_code == 501, response.text
    assert "SARDIS_RELIABILITY_SANDBOX=true" in response.json()["detail"]
