from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.providers.cache import CacheProvider, get_cache_provider
from app.repositories.complaint import ComplaintRepository
from app.services.complaint import ComplaintService
from app.services.triage import TriageService, get_triage_service


async def get_complaint_service(
    session: AsyncSession = Depends(get_db_session),
    cache_provider: CacheProvider = Depends(get_cache_provider),
    triage_service: TriageService = Depends(get_triage_service),
) -> ComplaintService:
    """Dependency that constructs ComplaintService with ComplaintRepository.
    Routes do NOT touch database sessions directly.
    """
    repository = ComplaintRepository(session)
    return ComplaintService(
        repository=repository,
        triage_svc=triage_service,
        cache_prov=cache_provider,
    )
