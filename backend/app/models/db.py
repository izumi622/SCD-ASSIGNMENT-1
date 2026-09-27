import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator


class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36) for SQLite.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(value)


class ComplaintDB(Base):
    __tablename__ = "complaints"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    text = Column(String(2000), nullable=False)
    location = Column(String(200), nullable=False)
    reporter_contact = Column(String(255), nullable=True)

    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    ai_summary = Column(String(140), nullable=True)
    triaged_by = Column(String(64), nullable=False)
    triage_latency_ms = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("length(text) >= 10", name="chk_complaint_text_min_length"),
        CheckConstraint("length(text) <= 2000", name="chk_complaint_text_max_length"),
        CheckConstraint("length(location) >= 3", name="chk_complaint_location_min_length"),
        CheckConstraint("length(location) <= 200", name="chk_complaint_location_max_length"),
        Index("ix_complaints_status_priority", "status", "priority"),
        Index("ix_complaints_created_at", "created_at"),
    )
