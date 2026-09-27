import pytest
from pydantic import ValidationError

from app.models.enums import Category, Priority, Status
from app.models.schemas import ComplaintCreate, ComplaintStatusUpdate


def test_complaint_create_validation():
    # Valid
    c = ComplaintCreate(
        text="Water pipeline has broken in sector F-7",
        location="Sector F-7 Street 15",
        reporter_contact="user@test.com",
    )
    assert c.text == "Water pipeline has broken in sector F-7"

    # Too short text (< 10 chars)
    with pytest.raises(ValidationError):
        ComplaintCreate(text="Short", location="Valid location")

    # Too short location (< 3 chars)
    with pytest.raises(ValidationError):
        ComplaintCreate(text="Valid length complaint text here", location="No")


def test_status_update_validation():
    s = ComplaintStatusUpdate(status=Status.in_progress)
    assert s.status == Status.in_progress


def test_enum_members():
    assert Category.water.value == "water"
    assert Priority.high.value == "high"
    assert Status.open.value == "open"
