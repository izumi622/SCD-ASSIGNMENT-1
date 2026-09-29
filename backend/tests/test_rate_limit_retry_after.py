import pytest


async def test_retry_after_matches_sliding_window_expiry(test_cache, monkeypatch):
    now = [59.5]
    monkeypatch.setattr("app.providers.cache.time.time", lambda: now[0])
    assert await test_cache.check_rate_limit("client", limit=1) == (True, 0)
    now[0] = 60.0
    assert await test_cache.check_rate_limit("client", limit=1) == (False, 60)
    now[0] = 119.5
    assert await test_cache.check_rate_limit("client", limit=1) == (True, 0)


@pytest.mark.parametrize("limit,window", [(0, 60), (-1, 60), (1, 0), (1, -1)])
async def test_invalid_rate_limit_parameters_fail_clearly(test_cache, limit, window):
    with pytest.raises(ValueError, match="must be positive"):
        await test_cache.check_rate_limit("client", limit=limit, window_seconds=window)
