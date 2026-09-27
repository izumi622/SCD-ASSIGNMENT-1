import pytest


@pytest.mark.asyncio
async def test_cors_headers_on_options_request(client):
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
    }
    response = await client.options("/api/complaints", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


@pytest.mark.asyncio
async def test_x_request_id_in_response(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
