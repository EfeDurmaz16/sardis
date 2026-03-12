from pathlib import Path
from types import SimpleNamespace
import sys


ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sardis_protocol.verifier import MandateVerifier


def test_verifier_passes_redis_url_to_rate_limiter(monkeypatch):
    captured: dict[str, object] = {}

    def fake_get_rate_limiter(config=None, redis_url=None):
        captured["config"] = config
        captured["redis_url"] = redis_url
        return object()

    monkeypatch.setenv("SARDIS_REDIS_URL", "rediss://example-redis")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_URL", raising=False)
    monkeypatch.setattr("sardis_protocol.verifier.get_rate_limiter", fake_get_rate_limiter)

    MandateVerifier(settings=SimpleNamespace())

    assert captured["redis_url"] == "rediss://example-redis"
