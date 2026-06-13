"""Regression: 5xx responses map to APIStatusError subclasses.

A 5xx must be catchable via ``except sardis.APIStatusError`` (the documented
contract) — previously they fell through to a bare ``APIError``.
"""

from __future__ import annotations

import httpx
import pytest

from sardis import Sardis
from sardis.models.errors import (
    APIError,
    APIStatusError,
    BadGatewayError,
    GatewayTimeoutError,
    ServerError,
    ServiceUnavailableError,
)


def _resp(status: int) -> httpx.Response:
    return httpx.Response(
        status,
        json={"error": {"message": f"upstream {status}"}},
        request=httpx.Request("POST", "https://api.sardis.sh/v2/pay"),
    )


@pytest.mark.parametrize(
    ("status", "cls"),
    [
        (500, ServerError),
        (502, BadGatewayError),
        (503, ServiceUnavailableError),
        (504, GatewayTimeoutError),
        (520, ServerError),  # any other 5xx -> ServerError
    ],
)
def test_5xx_maps_to_apistatuserror_subclass(status: int, cls: type[Exception]) -> None:
    client = Sardis(api_key="unit-test-key")
    with pytest.raises(cls) as exc_info:
        client._handle_error_response(_resp(status))
    err = exc_info.value
    # Caught by the one documented "any status error" clause:
    assert isinstance(err, APIStatusError)
    assert isinstance(err, APIError)
    assert err.status_code == status
