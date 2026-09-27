import pytest
from app.providers.metrics import (
    HTTP_REQUESTS_TOTAL,
    TRIAGE_FALLBACK_TOTAL,
    TRIAGE_DURATION_SECONDS,
)


def test_metrics_definitions():
    assert HTTP_REQUESTS_TOTAL is not None
    assert TRIAGE_FALLBACK_TOTAL is not None
    assert TRIAGE_DURATION_SECONDS is not None


@pytest.mark.asyncio
async def test_metrics_scraped_via_client(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
