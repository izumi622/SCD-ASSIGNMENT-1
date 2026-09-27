import uuid

import pytest

from app.models.enums import Category, Priority


@pytest.mark.asyncio
async def test_create_complaint_success(client):
    payload = {
        "text": "Main water pipeline burst flooding Street 12 since fajr",
        "location": "Street 12, G-8/1, Islamabad",
        "reporter_contact": "+92-300-1234567",
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["text"] == payload["text"]
    assert data["location"] == payload["location"]
    assert data["reporter_contact"] == payload["reporter_contact"]
    assert data["status"] == "open"
    assert data["category"] in [c.value for c in Category]
    assert data["priority"] in [p.value for p in Priority]
    assert "id" in data
    assert "triage_latency_ms" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_complaint_validation_error(client):
    """Field-level error body must be returned with 400 Bad Request."""
    # Text too short (< 10 chars)
    payload = {
        "text": "Too short",
        "location": "Loc",
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
    loc_fields = [e["loc"][-1] for e in data["detail"]]
    assert "text" in loc_fields


@pytest.mark.asyncio
async def test_get_complaint_by_id(client):
    # 1. Create a complaint
    post_res = await client.post(
        "/api/complaints",
        json={"text": "Electrical wiring sparking on tree branch", "location": "Sector F-6"},
    )
    cid = post_res.json()["id"]

    # 2. Fetch by ID
    get_res = await client.get(f"/api/complaints/{cid}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == cid

    # 3. Non-existent ID returns 404
    non_existent = str(uuid.uuid4())
    not_found_res = await client.get(f"/api/complaints/{non_existent}")
    assert not_found_res.status_code == 404


@pytest.mark.asyncio
async def test_list_and_filter_complaints(client):
    # Seed 3 distinct complaints
    await client.post(
        "/api/complaints",
        json={"text": "Water pipeline leaking in basement", "location": "Sector G-9"},
    )
    await client.post(
        "/api/complaints",
        json={"text": "Road pothole near commercial market", "location": "Commercial Area"},
    )
    await client.post(
        "/api/complaints",
        json={"text": "Garbage pile lying near main gate", "location": "Residential Block"},
    )

    # List all
    res = await client.get("/api/complaints?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
    assert data["page"] == 1
    assert data["page_size"] == 10

    # Filter by category
    water_res = await client.get("/api/complaints?category=water")
    assert water_res.status_code == 200
    for item in water_res.json()["items"]:
        assert item["category"] == "water"


@pytest.mark.asyncio
async def test_rate_limiter_exceeded_returns_429(client, test_cache):
    """Exceeding rate limit returns 429 with Retry-After header."""
    # Temporarily set limit to 2
    for _ in range(2):
        res = await client.post(
            "/api/complaints",
            json={
                "text": "Testing rate limit counter in rapid succession",
                "location": "Sector H-8",
            },
        )
        assert res.status_code == 201

    # Force limit to be exceeded on next request
    client_ip = "127.0.0.1"
    # Artificially trigger limit exceeded
    for _ in range(100):
        test_cache._in_memory_rate_limits.setdefault(client_ip, []).append(9999999999)

    rate_limited_res = await client.post(
        "/api/complaints",
        json={"text": "This request should be blocked by rate limiter", "location": "Sector H-8"},
    )
    assert rate_limited_res.status_code == 429
    assert "Retry-After" in rate_limited_res.headers
    assert int(rate_limited_res.headers["Retry-After"]) > 0
