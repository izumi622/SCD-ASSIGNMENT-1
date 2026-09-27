from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status

from app.models.db import ComplaintDB
from app.models.enums import Status, is_valid_transition
from app.models.schemas import ComplaintCreate, ComplaintStatusUpdate
from app.providers.cache import CacheProvider
from app.repositories.complaint import ComplaintRepository
from app.services.triage import TriageService, get_triage_service


class ComplaintService:
    """Business logic service for complaint intake, triage orchestration,
    status transition state machine enforcement, and cached statistics.
    No SQL queries live here.
    """

    def __init__(
        self,
        repository: ComplaintRepository,
        triage_svc: TriageService | None = None,
        cache_prov: CacheProvider | None = None,
    ) -> None:
        self.repository = repository
        self.triage_service = triage_svc or get_triage_service()
        self.cache_provider = cache_prov or CacheProvider()

    async def create_complaint(self, data: ComplaintCreate) -> ComplaintDB:
        """Validates, triages with AI/rules, and persists new complaint."""
        # 1. AI Triage step
        triage_result, triaged_by, latency_ms = await self.triage_service.triage_complaint(
            text=data.text,
            location=data.location,
        )

        # 2. Construct persistent entity
        complaint = ComplaintDB(
            text=data.text,
            location=data.location,
            reporter_contact=data.reporter_contact,
            category=triage_result.category.value,
            priority=triage_result.priority.value,
            status=Status.open.value,
            ai_summary=triage_result.summary,
            triaged_by=triaged_by,
            triage_latency_ms=latency_ms,
        )

        # 3. Persist via repository
        saved = await self.repository.create(complaint)

        # 4. Invalidate stats cache on write
        await self.cache_provider.invalidate_stats_cache()

        return saved

    async def get_complaint(self, complaint_id: UUID) -> ComplaintDB:
        """Retrieves complaint by ID or raises 404."""
        complaint = await self.repository.get_by_id(complaint_id)
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID '{complaint_id}' not found",
            )
        return complaint

    async def list_complaints(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ComplaintDB], int]:
        """Lists complaints matching criteria with pagination."""
        if page_size > 100:
            page_size = 100
        if page < 1:
            page = 1

        return await self.repository.list_complaints(
            category=category,
            priority=priority,
            status=status_filter,
            page=page,
            page_size=page_size,
        )

    async def update_status(self, complaint_id: UUID, update: ComplaintStatusUpdate) -> ComplaintDB:
        """Enforces status state machine table.
        Throws 409 Conflict naming the attempted transition if invalid.
        """
        complaint = await self.get_complaint(complaint_id)
        current_status = Status(complaint.status)
        target_status = update.status

        # Enforce transition table (§2.2)
        if not is_valid_transition(current_status, target_status):
            error_message = (
                f"Invalid transition from {current_status.value} to {target_status.value}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_message,
            )

        updated = await self.repository.update_status(complaint, target_status.value)

        # Invalidate stats cache on write
        await self.cache_provider.invalidate_stats_cache()

        return updated

    async def get_stats(self) -> Tuple[Dict[str, Any], bool]:
        """Fetches aggregate stats using 30s read-through Redis cache.
        Returns: (stats_dict, is_cache_hit)
        """
        cached, is_hit = await self.cache_provider.get_stats_cache()
        if is_hit and cached is not None:
            return cached, True

        # Cache miss: query persistence repository
        stats = await self.repository.get_stats()

        # Cache in Redis with 30s TTL
        await self.cache_provider.set_stats_cache(stats, ttl_seconds=30)
        return stats, False
