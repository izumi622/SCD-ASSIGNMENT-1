import pytest
from app.models.db import ComplaintDB
from app.models.enums import Category, Priority, Status
from app.repositories.complaint import ComplaintRepository


@pytest.mark.asyncio
async def test_repository_crud(db_session):
    repo = ComplaintRepository(db_session)

    complaint = ComplaintDB(
        text="Dangerous electrical sparking from transformer",
        location="Main Bazaar near Post Office",
        reporter_contact="resident@bazaar.org",
        category=Category.electricity.value,
        priority=Priority.high.value,
        status=Status.open.value,
        ai_summary="Dangerous transformer sparking",
        triaged_by="simulated",
        triage_latency_ms=45,
    )
    created = await repo.create(complaint)

    assert created.id is not None
    assert created.status == Status.open.value

    # Fetch by ID
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.category == Category.electricity.value

    # List & filter
    items, total = await repo.list_complaints(category=Category.electricity.value, page=1, page_size=10)
    assert total >= 1
    assert any(i.id == created.id for i in items)

    # Update status
    updated = await repo.update_status(created, Status.in_progress.value)
    assert updated.status == Status.in_progress.value

    # Stats
    stats = await repo.get_stats()
    assert stats["total_complaints"] >= 1
