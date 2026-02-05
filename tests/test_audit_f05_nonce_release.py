"""Test F05: Nonce is only released when broadcast fails, not on confirmation failure.

Tests the broadcast_success flag pattern in ChainExecutor that guards nonce release.
"""
import inspect
import textwrap


def test_broadcast_success_flag_exists():
    """Verify broadcast_success flag is initialized before broadcast."""
    from sardis_chain.executor import ChainExecutor
    source = inspect.getsource(ChainExecutor)
    assert "broadcast_success = False" in source, (
        "ChainExecutor must initialize broadcast_success = False before broadcast"
    )


def test_broadcast_success_set_after_send():
    """Verify broadcast_success is set to True after successful send."""
    from sardis_chain.executor import ChainExecutor
    source = inspect.getsource(ChainExecutor)
    assert "broadcast_success = True" in source, (
        "ChainExecutor must set broadcast_success = True after send_raw_transaction"
    )
    # Ensure the flag is set AFTER send_raw_transaction
    send_pos = source.index("send_raw_transaction")
    flag_set_pos = source.index("broadcast_success = True")
    assert flag_set_pos > send_pos, (
        "broadcast_success = True must appear after send_raw_transaction call"
    )


def test_nonce_release_guarded_by_broadcast_flag():
    """Verify nonce release only happens when broadcast_success is False."""
    from sardis_chain.executor import ChainExecutor
    source = inspect.getsource(ChainExecutor)
    assert "if not broadcast_success:" in source, (
        "Nonce release must be guarded by 'if not broadcast_success:' check"
    )
    # Verify release_nonce appears after the guard
    guard_pos = source.index("if not broadcast_success:")
    release_pos = source.index("release_nonce", guard_pos)
    assert release_pos > guard_pos, (
        "release_nonce must appear inside the 'if not broadcast_success' block"
    )


def test_nonce_not_released_unconditionally():
    """Verify there's no unconditional release_nonce in the exception handler."""
    from sardis_chain.executor import ChainExecutor
    source = inspect.getsource(ChainExecutor)
    # Find the except block that handles nonce release
    except_blocks = source.split("except Exception as e:")
    for block in except_blocks:
        if "release_nonce" in block:
            # This block must contain the broadcast_success guard
            assert "broadcast_success" in block, (
                "Any except block with release_nonce must check broadcast_success"
            )
