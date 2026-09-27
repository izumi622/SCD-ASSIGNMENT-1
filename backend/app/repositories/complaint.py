from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import ComplaintDB


class ComplaintRepository:
    """Persistence repository for Complaint domain entity.
    All SQL operations live strictly inside this repository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, complaint: ComplaintDB) -> ComplaintDB:
        """Persists a new complaint."""
        self.session.add(complaint)
        await self.session.flush()
        await self.session.refresh(complaint)
        return complaint

    async def get_by_id(self, complaint_id: UUID) -> Optional[ComplaintDB]:
        """Fetches complaint by its UUID."""
        stmt = select(ComplaintDB).where(ComplaintDB.id == complaint_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_complaints(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ComplaintDB], int]:
        """Filters and paginates complaints, returning (items, total_count)."""
        base_query = select(ComplaintDB)

        if category:
            base_query = base_query.where(ComplaintDB.category == category)
        if priority:
            base_query = base_query.where(ComplaintDB.priority == priority)
        if status:
            base_query = base_query.where(ComplaintDB.status == status)

        # Count total matching records
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply ordering and pagination
        offset = (page - 1) * page_size
        query = base_query.order_by(ComplaintDB.created_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update_status(self, complaint: ComplaintDB, new_status: str) -> ComplaintDB:
        """Updates the status of a complaint and commits."""
        complaint.status = new_status
        await self.session.flush()
        await self.session.refresh(complaint)
        return complaint

    async def get_stats(self) -> Dict[str, Any]:
        """Calculates aggregate counts by category, priority, and status."""
        total_stmt = select(func.count(ComplaintDB.id))
        total_res = await self.session.execute(total_stmt)
        total_complaints = total_res.scalar_one()

        # Counts by category
        cat_stmt: Any = select(ComplaintDB.category, func.count(ComplaintDB.id)).group_by(
            ComplaintDB.category
        )
        cat_res = await self.session.execute(cat_stmt)
        by_category = {cat: count for cat, count in cat_res.all()}

        # Counts by priority
        prio_stmt: Any = select(ComplaintDB.priority, func.count(ComplaintDB.id)).group_by(
            ComplaintDB.priority
        )
        prio_res = await self.session.execute(prio_stmt)
        by_priority = {prio: count for prio, count in prio_res.all()}

        # Counts by status
        status_stmt: Any = select(ComplaintDB.status, func.count(ComplaintDB.id)).group_by(
            ComplaintDB.status
        )
        status_res = await self.session.execute(status_stmt)
        by_status = {st: count for st, count in status_res.all()}

        return {
            "total_complaints": total_complaints,
            "by_category": by_category,
            "by_priority": by_priority,
            "by_status": by_status,
        }
