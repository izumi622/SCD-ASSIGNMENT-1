from unittest.mock import AsyncMock, Mock

from app.providers.cache import CacheProvider


async def test_failed_ping_closes_client_and_bounds_operations(monkeypatch, caplog):
    redis = AsyncMock()
    redis.ping.side_effect = RuntimeError("sensitive connection value")
    factory = Mock(return_value=redis)
    monkeypatch.setattr("app.providers.cache.aioredis.from_url", factory)
    cache = CacheProvider(redis_url="redis://localhost:6379")
    assert await cache.get_redis() is None
    redis.aclose.assert_awaited_once()
    assert factory.call_args.kwargs["socket_timeout"] == 0.5
    assert "sensitive connection value" not in caplog.text
    assert await cache.get_redis() is None
    factory.assert_called_once()


async def test_close_releases_connection(test_cache):
    connection = AsyncMock()
    test_cache._redis = connection
    await test_cache.close()
    connection.aclose.assert_awaited_once()
    assert test_cache._redis is None
