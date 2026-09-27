import uuid
import pytest
from fastapi import HTTPException
from app.models.enums import Status
from app.models.schemas import ComplaintCreate, ComplaintStatusUpdate
from app.repositories.complaint import ComplaintRepository
from app.services.complaint import ComplaintService


@pytest.mark.asyncio
async def test_service_status_transition_rules(db_session, test_cache, test_triage_service):
    repo = ComplaintRepository(db_session)
    service = ComplaintService(
        repository=repo,
        triage_svc=test_triage_service,
        cache_prov=test_cache,
    )

    complaint = await service.create_complaint(
        ComplaintCreate(
            text="Garbage pile accumulating on side of the street",
            location="Commercial Market Block B",
        )
    )

    # Valid: open -> in_progress
    updated = await service.update_status(
        complaint.id,
        ComplaintStatusUpdate(status=Status.in_progress),
    )
    assert updated.status == Status.in_progress.value

    # Invalid: in_progress -> open (should raise 409 Conflict)
    with pytest.raises(HTTPException) as exc_info:
        await service.update_status(
            complaint.id,
            ComplaintStatusUpdate(status=Status.open),
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_service_get_nonexistent_complaint(db_session, test_cache, test_triage_service):
    repo = ComplaintRepository(db_session)
    service = ComplaintService(
        repository=repo,
        triage_svc=test_triage_service,
        cache_prov=test_cache,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_complaint(uuid.uuid4())
    assert exc_info.value.status_code == 404
