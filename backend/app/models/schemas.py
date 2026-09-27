from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Category, Priority, Status


class ComplaintCreate(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Complaint text description (10-2000 chars)",
    )
    location: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Complaint location description (3-200 chars)",
    )
    reporter_contact: Optional[str] = Field(
        None, max_length=255, description="Optional reporter contact info"
    )


class ComplaintStatusUpdate(BaseModel):
    status: Status = Field(..., description="Target status for state machine transition")


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    location: str
    reporter_contact: Optional[str] = None
    category: Category
    priority: Priority
    status: Status
    ai_summary: Optional[str] = None
    triaged_by: str
    triage_latency_ms: int
    created_at: datetime
    updated_at: datetime


class ComplaintListResponse(BaseModel):
    items: List[ComplaintResponse]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    total_complaints: int
    by_category: Dict[str, int]
    by_priority: Dict[str, int]
    by_status: Dict[str, int]


class TriageOutcome(BaseModel):
    provider: str
    latency_ms: int
    fallback: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProvidersMetaResponse(BaseModel):
    active_provider: str
    recent_outcomes: List[TriageOutcome]


class ErrorDetail(BaseModel):
    loc: List[str]
    msg: str
    type: str


class HTTPValidationErrorResponse(BaseModel):
    detail: List[ErrorDetail]
