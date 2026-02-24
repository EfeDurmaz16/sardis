from __future__ import annotations

from sardis_cards.providers.issuer_readiness import evaluate_issuer_readiness


def test_evaluate_issuer_readiness_returns_known_candidates(monkeypatch):
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_x")
    monkeypatch.setenv("LITHIC_API_KEY", "li_test_x")
    monkeypatch.delenv("RAIN_API_KEY", raising=False)
    monkeypatch.delenv("RAIN_PROGRAM_ID", raising=False)
    monkeypatch.delenv("BRIDGE_API_KEY", raising=False)

    items = evaluate_issuer_readiness()
    names = {item.name for item in items}
    assert {"stripe_issuing", "lithic", "rain", "bridge_cards"}.issubset(names)

    stripe = next(item for item in items if item.name == "stripe_issuing")
    rain = next(item for item in items if item.name == "rain")

    assert stripe.configured is True
    assert rain.configured is False
    assert "RAIN_API_KEY" in rain.missing_env
