"""Search routes for jobs."""

from typing import Annotated
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.routes.auth import get_current_user
from app.models.user import User
from app.models.job import Job
from app.models.tag import job_tags
from pydantic import BaseModel

router = APIRouter(tags=["search"])


class SearchMatch(BaseModel):
    """Search match with highlighting."""

    type: str  # "filename"
    text: str
    highlight: str


class SearchResultItem(BaseModel):
    """Individual search result."""

    job_id: str
    original_filename: str
    status: str
    created_at: datetime
    matches: list[SearchMatch]


class SearchResponse(BaseModel):
    """Search response with results."""

    query: str
    total: int
    items: list[SearchResultItem]


def highlight_text(text: str, query: str) -> str:
    """
    Wrap query matches in <mark> tags for highlighting.

    Args:
        text: Text to highlight
        query: Search query

    Returns:
        Text with query matches wrapped in <mark> tags
    """
    if query == "*":
        return text

    # Case-insensitive replacement
    import re

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group()}</mark>", text)


def create_matches(job: Job, query: str) -> list[SearchMatch]:
    """
    Create match objects for a job based on filename.

    Args:
        job: Job object
        query: Search query

    Returns:
        List of SearchMatch objects
    """
    matches = []

    # Check filename match
    if query == "*" or query.lower() in job.original_filename.lower():
        matches.append(
            SearchMatch(
                type="filename",
                text=job.original_filename,
                highlight=highlight_text(job.original_filename, query),
            )
        )

    return matches


@router.get("/search", response_model=SearchResponse)
async def search_jobs(
    q: Annotated[str, Query(min_length=1, description="Search query")],
    status: Annotated[str | None, Query()] = None,
    tags: Annotated[str | None, Query(description="Comma-separated tag IDs")] = None,
    date_from: Annotated[str | None, Query(description="ISO-8601 date")] = None,
    date_to: Annotated[str | None, Query(description="ISO-8601 date")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search jobs by filename.

    Supports filtering by:
    - Text query (searches filename only for MVP)
    - Status
    - Tags (AND logic for multiple tags)
    - Date range

    Args:
        q: Search query string (use "*" for all)
        status: Optional status filter
        tags: Optional comma-separated tag IDs
        date_from: Optional start date filter
        date_to: Optional end date filter
        limit: Results per page (default 50, max 100)
        offset: Pagination offset
        db: Database session
        current_user: Current authenticated user

    Returns:
        SearchResponse with matching jobs
    """
    # Build base query
    stmt = select(Job).where(Job.user_id == current_user.id).options(selectinload(Job.tags))

    # Apply search filter (filename only for MVP)
    if q != "*":
        stmt = stmt.where(Job.original_filename.ilike(f"%{q}%"))

    # Apply status filter
    if status:
        stmt = stmt.where(Job.status == status)

    # Apply tag filter
    if tags:
        tag_ids = [int(tid.strip()) for tid in tags.split(",")]

        # For each tag, job must have it (AND logic)
        for tag_id in tag_ids:
            tag_subquery = select(job_tags.c.job_id).where(job_tags.c.tag_id == tag_id)
            stmt = stmt.where(Job.id.in_(tag_subquery))

    # Apply date filters
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            stmt = stmt.where(Job.created_at >= date_from_dt)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date_from format. Use ISO-8601 format.",
            )

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            stmt = stmt.where(Job.created_at <= date_to_dt)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date_to format. Use ISO-8601 format.",
            )

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    stmt = stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)

    # Execute query
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    # Build response items
    items = []
    for job in jobs:
        # Create matches
        matches = create_matches(job, q)

        # Only include jobs that have matches
        if matches:
            items.append(
                SearchResultItem(
                    job_id=job.id,
                    original_filename=job.original_filename,
                    status=job.status,
                    created_at=job.created_at,
                    matches=matches,
                )
            )

    return SearchResponse(query=q, total=total, items=items)
