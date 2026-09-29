import logging

import httpx
import pytest

from app.providers.triage.simulated import SimulatedRateLimitError
from app.services.triage import is_retryable_exception


@pytest.mark.parametrize(
    "status,expected", [(400, False), (401, False), (429, True), (500, True), (503, True)]
)
def test_http_status_retry_policy(status, expected):
    request = httpx.Request("POST", "https://example.invalid")
    response = httpx.Response(status, request=request)
    assert (
        is_retryable_exception(httpx.HTTPStatusError("failure", request=request, response=response))
        is expected
    )


@pytest.mark.parametrize(
    "error,expected",
    [
        (TimeoutError(), True),
        (httpx.ReadTimeout("timeout"), True),
        (SimulatedRateLimitError(), True),
        (ValueError("invalid complaint 429 or 500"), False),
        (httpx.ConnectError("connection refused"), False),
    ],
)
def test_retry_uses_error_type_not_message(error, expected):
    assert is_retryable_exception(error) is expected


async def test_retry_logs_do_not_include_exception_payload(
    test_triage_service, monkeypatch, caplog
):
    sensitive = "private-contact-and-api-token"

    def fail(*args):
        raise TimeoutError(sensitive)

    monkeypatch.setattr(test_triage_service.provider, "triage", fail)
    monkeypatch.setattr("app.services.triage.random.uniform", lambda *args: 0)
    with caplog.at_level(logging.INFO):
        _, provider, _ = await test_triage_service.triage_complaint("Water leak", "Block A")
    assert provider == "rules:fallback"
    assert "Retrying triage" in caplog.text
    assert sensitive not in caplog.text
