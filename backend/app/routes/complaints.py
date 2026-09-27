from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.config import get_settings
from app.models.enums import Category, Priority, Status
from app.models.schemas import (
    ComplaintCreate,
    ComplaintListResponse,
    ComplaintResponse,
    ComplaintStatusUpdate,
    ProvidersMetaResponse,
    StatsResponse,
)
from app.providers.cache import CacheProvider, get_cache_provider
from app.routes.deps import get_complaint_service
from app.services.complaint import ComplaintService
from app.services.triage import TriageService, get_triage_service

router = APIRouter(prefix="/api", tags=["Complaints"])
settings = get_settings()


def get_client_ip(request: Request) -> str:
    """Extracts client IP, respecting X-Forwarded-For if behind a reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post(
    "/complaints",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a citizen complaint",
    description="Validates, triages via AI or fallback rules, and persists a citizen complaint.",
)
async def create_complaint(
    request: Request,
    complaint_in: ComplaintCreate,
    service: ComplaintService = Depends(get_complaint_service),
    cache: CacheProvider = Depends(get_cache_provider),
) -> ComplaintResponse:
    # Distributed Rate Limiting (Redis)
    client_ip = get_client_ip(request)
    allowed, retry_after = await cache.check_rate_limit(
        client_ip=client_ip,
        limit=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Too many requests.",
            headers={"Retry-After": str(retry_after)},
        )

    saved_complaint = await service.create_complaint(complaint_in)
    return ComplaintResponse.model_validate(saved_complaint)


@router.get(
    "/complaints/{complaint_id}",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complaint by ID",
)
async def get_complaint(
    complaint_id: UUID,
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintResponse:
    complaint = await service.get_complaint(complaint_id)
    return ComplaintResponse.model_validate(complaint)


@router.get(
    "/complaints",
    response_model=ComplaintListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter complaints",
)
async def list_complaints(
    category: Optional[Category] = Query(None, description="Filter by category"),
    priority: Optional[Priority] = Query(None, description="Filter by priority"),
    status: Optional[Status] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintListResponse:
    items, total = await service.list_complaints(
        category=category.value if category else None,
        priority=priority.value if priority else None,
        status_filter=status.value if status else None,
        page=page,
        page_size=page_size,
    )
    return ComplaintListResponse(
        items=[ComplaintResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/complaints/{complaint_id}/status",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
    summary="Advance complaint status",
    description="Enforces explicit transition table. Returns 409 naming attempted transition on invalid state change.",
)
async def update_complaint_status(
    complaint_id: UUID,
    status_update: ComplaintStatusUpdate,
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintResponse:
    updated = await service.update_status(complaint_id, status_update)
    return ComplaintResponse.model_validate(updated)


@router.get(
    "/stats",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Aggregated complaint statistics",
    description="Redis-cached with 30s TTL. Sets X-Cache: HIT or X-Cache: MISS header.",
)
async def get_stats(
    response: Response,
    service: ComplaintService = Depends(get_complaint_service),
) -> StatsResponse:
    stats_data, is_hit = await service.get_stats()
    response.headers["X-Cache"] = "HIT" if is_hit else "MISS"
    return StatsResponse.model_validate(stats_data)


@router.get(
    "/meta/providers",
    response_model=ProvidersMetaResponse,
    status_code=status.HTTP_200_OK,
    summary="Triage providers metadata & rolling observability window",
)
async def get_providers_metadata(
    triage_service: TriageService = Depends(get_triage_service),
) -> ProvidersMetaResponse:
    return ProvidersMetaResponse(
        active_provider=settings.TRIAGE_PROVIDER,
        recent_outcomes=triage_service.get_recent_outcomes(),
    )
