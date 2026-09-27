import pytest

from app.providers.triage.base import TriageProvider, TriageResult
from app.services.triage import TriageService


class FailingProvider(TriageProvider):
    name = "failing_mock"

    def triage(self, text: str, location: str) -> TriageResult:
        raise ConnectionError("Remote LLM service is completely unreachable")


@pytest.mark.asyncio
async def test_explicit_fallback_on_provider_exception(test_cache):
    """
    Explicit test asserting fallback to RuleBasedTriage on provider exception,
    verifying triaged_by = 'rules:fallback'.
    """
    failing_provider = FailingProvider()
    service = TriageService(
        provider=failing_provider,
        cache=test_cache,
    )

    result, triaged_by, latency = await service.triage_complaint(
        text="Massive garbage pile and rotting trash dumping near school",
        location="Sector I-8 Islamabad",
    )
    assert result.category.value == "sanitation"
    assert triaged_by == "rules:fallback"
    assert result.summary != ""
