import pytest


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        "not JSON",
        {"category": "hacked"},
        {"category": "water", "priority": "high", "summary": "x" * 141, "confidence": 0.8},
    ],
)
async def test_invalid_provider_return_falls_back(test_triage_service, monkeypatch, invalid):
    calls = []

    def malformed(*args):
        calls.append(args)
        return invalid

    monkeypatch.setattr(test_triage_service.provider, "triage", malformed)
    result, provider, _ = await test_triage_service.triage_complaint("Water pipe burst", "Block A")
    assert provider == "rules:fallback"
    assert result.category.value == "water"
    assert len(calls) == 1
    key = test_triage_service._compute_hash("Water pipe burst", "Block A")
    assert await test_triage_service.cache.get_triage_cache(key) is None
