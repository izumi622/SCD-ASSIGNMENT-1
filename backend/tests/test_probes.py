import uuid
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_liveness_probe(client):
    """Liveness probe must return 200 without touching database."""
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_readiness_probe_healthy(client):
    """Readiness probe returns 200 when backing dependencies are reachable."""
    with patch(
        "app.providers.cache.CacheProvider.get_redis", new_callable=AsyncMock
    ) as mock_get_redis:
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis

        res = await client.get("/ready")
        assert res.status_code == 200
        assert res.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_readiness_probe_dependency_failure(client):
    """Readiness probe returns 503 naming the failed dependency."""
    # Simulate Redis failure
    with patch(
        "app.providers.cache.CacheProvider.get_redis", new_callable=AsyncMock
    ) as mock_get_redis:
        mock_get_redis.return_value = None

        res = await client.get("/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unready"
        assert "redis" in data["failed_dependency"]


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client):
    """Prometheus endpoint returns valid text format metrics."""
    res = await client.get("/metrics")
    assert res.status_code == 200
    content = res.text
    assert "http_requests_total" in content
    assert "http_request_duration_seconds" in content
    assert "triage_duration_seconds" in content
    assert "triage_fallback_total" in content


@pytest.mark.asyncio
async def test_request_id_propagation(client):
    custom_req_id = "test-request-id-12345"
    res = await client.get("/health", headers={"X-Request-ID": custom_req_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_req_id

    # Auto-generated when absent
    res_auto = await client.get("/health")
    auto_id = res_auto.headers.get("X-Request-ID")
    assert auto_id is not None
    # Validate UUID format
    parsed_uuid = uuid.UUID(auto_id)
    assert str(parsed_uuid) == auto_id
