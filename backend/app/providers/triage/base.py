from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.models.enums import Category, Priority


class TriageResult(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(..., max_length=140, description="One-line summary <= 140 chars")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )


@runtime_checkable
class TriageProvider(Protocol):
    name: str

    def triage(self, text: str, location: str) -> TriageResult:
        """Synchronously triage complaint text and location into a TriageResult."""
        ...
