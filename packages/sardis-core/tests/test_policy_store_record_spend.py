from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sardis_v2_core.policy_store_memory import InMemoryPolicyStore
from sardis_v2_core.spending_policy import create_default_policy


def test_record_spend_updates_totals_and_windows():
    store = InMemoryPolicyStore()
    agent_id = "agent_test_1"
    policy = create_default_policy(agent_id)
    asyncio.run(store.set_policy(agent_id, policy))

    asyncio.run(store.record_spend(agent_id, Decimal("10.0")))
    updated = asyncio.run(store.fetch_policy(agent_id))
    assert updated is not None
    assert updated.spent_total == Decimal("10.0")
    assert updated.daily_limit is not None
    assert updated.daily_limit.current_spent == Decimal("10.0")


def test_record_spend_resets_expired_window():
    store = InMemoryPolicyStore()
    agent_id = "agent_test_2"
    policy = create_default_policy(agent_id)
    assert policy.daily_limit is not None
    policy.daily_limit.current_spent = Decimal("90.0")
    policy.daily_limit.window_start = datetime.now(timezone.utc) - timedelta(days=2)
    asyncio.run(store.set_policy(agent_id, policy))

    asyncio.run(store.record_spend(agent_id, Decimal("5.0")))
    updated = asyncio.run(store.fetch_policy(agent_id))
    assert updated is not None
    assert updated.daily_limit is not None
    assert updated.daily_limit.current_spent == Decimal("5.0")


def test_record_spend_creates_default_policy_if_missing():
    store = InMemoryPolicyStore()
    agent_id = "agent_test_3"

    asyncio.run(store.record_spend(agent_id, Decimal("1.0")))
    updated = asyncio.run(store.fetch_policy(agent_id))
    assert updated is not None
    assert updated.spent_total == Decimal("1.0")
