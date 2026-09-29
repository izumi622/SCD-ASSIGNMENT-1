import json
from unittest.mock import AsyncMock

import pytest


@pytest.mark.parametrize("payload", [None, {"category": "water"}])
async def test_metric_failure_does_not_change_cache_result(test_cache, monkeypatch, payload):
    redis = AsyncMock()
    redis.get.return_value = json.dumps(payload) if payload is not None else None
    redis.incr.side_effect = RuntimeError("counter unavailable")
    monkeypatch.setattr(test_cache, "get_redis", AsyncMock(return_value=redis))
    assert await test_cache.get_triage_cache("hash") == payload
    assert test_cache._triage_hits == int(payload is not None)
    assert test_cache._triage_misses == int(payload is None)
