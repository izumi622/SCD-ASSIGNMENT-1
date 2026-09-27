import pytest

from app.seed import seed_database


@pytest.mark.asyncio
async def test_seed_database_idempotent(db_session):
    """Verifies that seed_database inserts >= 30 complaints on first run,
    and 0 duplicate complaints on second run (idempotency contract).
    """
    first_run_count = await seed_database(session=db_session)
    assert first_run_count >= 30, f"Expected at least 30 complaints, got {first_run_count}"

    second_run_count = await seed_database(session=db_session)
    assert second_run_count == 0, f"Expected 0 on second run (idempotent), got {second_run_count}"
