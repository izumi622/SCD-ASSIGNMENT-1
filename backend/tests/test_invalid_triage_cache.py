async def test_invalid_cached_schema_is_recomputed(test_triage_service):
    text, location = "Water leak", "Block A"
    key = test_triage_service._compute_hash(text, location)
    await test_triage_service.cache.set_triage_cache(key, {"category": "invalid"})
    result, provider, _ = await test_triage_service.triage_complaint(text, location)
    assert provider == "simulated"
    assert result.category.value == "water"
    repaired = await test_triage_service.cache.get_triage_cache(key)
    assert repaired["category"] == "water"
    assert repaired["triaged_by"] == "simulated"
