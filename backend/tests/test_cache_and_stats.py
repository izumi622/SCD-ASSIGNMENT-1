import pytest


@pytest.mark.asyncio
async def test_stats_read_through_cache_and_invalidation(client):
    # 1. First stats call should be a cache MISS
    res1 = await client.get("/api/stats")
    assert res1.status_code == 200
    assert res1.headers.get("X-Cache") == "MISS"
    data1 = res1.json()
    assert "total_complaints" in data1
    assert "by_category" in data1
    assert "by_priority" in data1
    assert "by_status" in data1

    # 2. Immediate second call should be a cache HIT
    res2 = await client.get("/api/stats")
    assert res2.status_code == 200
    assert res2.headers.get("X-Cache") == "HIT"

    # 3. Create a new complaint (triggers write invalidation)
    post_res = await client.post(
        "/api/complaints",
        json={"text": "Water pipeline burst causing street flooding", "location": "Lane 5"},
    )
    assert post_res.status_code == 201

    # 4. Next stats call after write must be a cache MISS (reflecting updated counts immediately)
    res3 = await client.get("/api/stats")
    assert res3.status_code == 200
    assert res3.headers.get("X-Cache") == "MISS"
    assert res3.json()["total_complaints"] == data1["total_complaints"] + 1


@pytest.mark.asyncio
async def test_providers_metadata_endpoint(client):
    res = await client.get("/api/meta/providers")
    assert res.status_code == 200
    data = res.json()
    assert "active_provider" in data
    assert "recent_outcomes" in data
    assert isinstance(data["recent_outcomes"], list)
