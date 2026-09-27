import pytest
from app.providers.cache import CacheProvider


@pytest.mark.asyncio
async def test_distributed_rate_limiter_isolated():
    """
    Tests rate limiter sliding-window algorithm, returning allowed status and remaining counts.
    """
    cache = CacheProvider(redis_url="none")
    ip = "192.168.1.100"

    # Allow 3 requests per minute
    allowed_1, _ = await cache.check_rate_limit(f"rate:{ip}", limit=3, window_seconds=60)
    allowed_2, _ = await cache.check_rate_limit(f"rate:{ip}", limit=3, window_seconds=60)
    allowed_3, _ = await cache.check_rate_limit(f"rate:{ip}", limit=3, window_seconds=60)
    allowed_4, retry_after = await cache.check_rate_limit(f"rate:{ip}", limit=3, window_seconds=60)

    assert allowed_1 is True
    assert allowed_2 is True
    assert allowed_3 is True
    assert allowed_4 is False
    assert retry_after > 0
