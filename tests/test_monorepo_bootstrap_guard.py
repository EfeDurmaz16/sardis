"""Tests for monorepo sys.path bootstrap guard behavior."""

from sardis_api.main import _should_bootstrap_monorepo_sys_path


def test_monorepo_bootstrap_enabled_for_dev(monkeypatch) -> None:
    monkeypatch.delenv("SARDIS_DISABLE_MONOREPO_BOOTSTRAP", raising=False)
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")
    assert _should_bootstrap_monorepo_sys_path() is True


def test_monorepo_bootstrap_disabled_for_production(monkeypatch) -> None:
    monkeypatch.delenv("SARDIS_DISABLE_MONOREPO_BOOTSTRAP", raising=False)
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    assert _should_bootstrap_monorepo_sys_path() is False


def test_monorepo_bootstrap_can_be_force_disabled(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_DISABLE_MONOREPO_BOOTSTRAP", "true")
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")
    assert _should_bootstrap_monorepo_sys_path() is False
