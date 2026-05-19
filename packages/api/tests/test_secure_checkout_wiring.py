from __future__ import annotations

import inspect


def test_main_wires_secure_checkout_router_with_flag():
    from sardis_server import main

    source = inspect.getsource(main)
    assert "secure_checkout_router.get_deps" in source
    assert "SARDIS_ENABLE_SECURE_CHECKOUT_EXECUTOR" in source
    assert "secure_checkout_router.router" in source
