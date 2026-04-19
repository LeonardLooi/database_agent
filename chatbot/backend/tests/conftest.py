from __future__ import annotations

import fakeredis
import pandas as pd
import pytest

from app.agent.clarification_state import ClarificationState
from app.agent.dataframe_store import DataFrameStore
from app.agent.tools.query_tools import AgentToolContext


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def store(fake_redis):
    return DataFrameStore(redis_client=fake_redis)


@pytest.fixture
def clarification_state(fake_redis):
    return ClarificationState(redis_client=fake_redis)


@pytest.fixture
def ctx(store, clarification_state):
    return AgentToolContext(
        user_id="u1",
        conversation_id="c1",
        store=store,
        clarification_state=clarification_state,
        websocket=None,
    )


@pytest.fixture
def sample_df():
    return pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Carol"], "amount": [100.0, 200.0, 300.0]})
