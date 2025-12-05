import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from sardis_api.main import create_app
from sardis_v2_core import SardisSettings
from tests.ap2_helpers import build_signed_bundle


def _sqlite(path: Path) -> str:
    return f"sqlite:///{path}"


def _settings(tmp_path: Path) -> SardisSettings:
    data_dir = tmp_path
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
        ledger_dsn=_sqlite(data_dir / "ledger.db"),
        mandate_archive_dsn=_sqlite(data_dir / "mandates.db"),
        replay_cache_dsn=_sqlite(data_dir / "replay.db"),
    )


def test_ap2_payment_execute_endpoint(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings=settings)
    client = TestClient(app)

    bundle = build_signed_bundle()
    response = client.post("/api/v2/ap2/payments/execute", json=bundle.model_dump())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert body["chain_tx_hash"].startswith("0x")
    assert body["compliance_provider"] == "rules"

    ledger_path = Path(settings.ledger_dsn.removeprefix("sqlite:///"))
    with sqlite3.connect(ledger_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()
        assert row[0] == 1
