"""Tag management routes."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.routes.auth import get_current_user
from app.models.user import User
from app.models.tag import Tag, job_tags
from app.models.job import Job
from app.schemas.tag import (
    TagCreate,
    TagUpdate,
    TagResponse,
    TagListResponse,
    TagAssignment,
    JobTagsResponse,
    TagBasic,
    TagDeleteResponse,
    TagRemoveResponse,
)

router = APIRouter(prefix="/tags", tags=["tags"])


def _scope_filter(scope: str | None, current_user: User):
    if scope == "global":
        return Tag.owner_user_id.is_(None)
    if scope == "personal":
        return Tag.owner_user_id == current_user.id
    return (Tag.owner_user_id.is_(None)) | (Tag.owner_user_id == current_user.id)


def _tag_scope(tag: Tag) -> str:
    return "global" if tag.owner_user_id is None else "personal"


@router.get("", response_model=TagListResponse)
async def list_tags(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    scope: str | None = Query(default=None, pattern="^(global|personal|all)$"),
):
    """List all tags with job counts."""
    # Get all tags with job counts
    join_clause = job_tags
    job_join = Job
    if current_user.is_admin:
        join_condition = Job.id == job_tags.c.job_id
    else:
        join_condition = (Job.id == job_tags.c.job_id) & (Job.user_id == current_user.id)

    stmt = select(Tag, func.count(Job.id).label("job_count")).select_from(Tag)
    stmt = stmt.outerjoin(join_clause, Tag.id == job_tags.c.tag_id).outerjoin(
        job_join, join_condition
    )
    if scope != "all":
        stmt = stmt.where(_scope_filter(scope, current_user))
    else:
        stmt = stmt.where(_scope_filter(None, current_user))
    stmt = stmt.group_by(Tag.id).order_by(Tag.created_at.desc())
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for tag, job_count in rows:
        items.append(
            TagResponse(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                scope=_tag_scope(tag),
                owner_user_id=tag.owner_user_id,
                job_count=job_count,
                created_at=tag.created_at,
            )
        )

    return TagListResponse(total=len(items), items=items)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create a new tag."""
    scope = tag_data.scope
    if not current_user.is_admin:
        scope = "personal"
    elif scope is None:
        scope = "global"

    owner_user_id = None if scope == "global" else current_user.id

    # Check if tag with same name exists in scope
    stmt = select(Tag).where(Tag.name == tag_data.name)
    if owner_user_id is None:
        stmt = stmt.where(Tag.owner_user_id.is_(None))
    else:
        stmt = stmt.where(Tag.owner_user_id == owner_user_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag with name '{tag_data.name}' already exists",
        )

    tag = Tag(name=tag_data.name, color=tag_data.color, owner_user_id=owner_user_id)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        scope=_tag_scope(tag),
        owner_user_id=tag.owner_user_id,
        job_count=0,
        created_at=tag.created_at,
    )


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update a tag's name or color."""
    # Get the tag
    stmt = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(stmt)
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.owner_user_id is None and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can modify global tags",
        )
    if (
        tag.owner_user_id is not None
        and tag.owner_user_id != current_user.id
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the tag owner can modify this tag",
        )

    # Check if new name conflicts with existing tag
    if tag_data.name and tag_data.name != tag.name:
        stmt = select(Tag).where(Tag.name == tag_data.name)
        if tag.owner_user_id is None:
            stmt = stmt.where(Tag.owner_user_id.is_(None))
        else:
            stmt = stmt.where(Tag.owner_user_id == tag.owner_user_id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag with name '{tag_data.name}' already exists",
            )
        tag.name = tag_data.name

    if tag_data.color is not None:
        tag.color = tag_data.color

    await db.commit()
    await db.refresh(tag)

    # Get job count
    stmt = select(func.count(job_tags.c.job_id)).where(job_tags.c.tag_id == tag.id)
    result = await db.execute(stmt)
    job_count = result.scalar() or 0

    return TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        scope=_tag_scope(tag),
        owner_user_id=tag.owner_user_id,
        job_count=job_count,
        created_at=tag.created_at,
    )


@router.delete("/{tag_id}", response_model=TagDeleteResponse)
async def delete_tag(
    tag_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Delete a tag (removes from all jobs)."""
    # Get the tag
    stmt = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(stmt)
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.owner_user_id is None and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete global tags",
        )
    if (
        tag.owner_user_id is not None
        and tag.owner_user_id != current_user.id
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the tag owner can delete this tag",
        )

    # Count affected jobs before deletion
    stmt = select(func.count(job_tags.c.job_id)).where(job_tags.c.tag_id == tag_id)
    result = await db.execute(stmt)
    jobs_affected = result.scalar() or 0

    # Delete the tag (cascade will remove job_tags entries)
    await db.delete(tag)
    await db.commit()

    return TagDeleteResponse(
        message="Tag deleted successfully", id=tag_id, jobs_affected=jobs_affected
    )


# Create separate router for job-tag associations (no prefix)
job_tags_router = APIRouter(tags=["tags"])


@job_tags_router.post("/jobs/{job_id}/tags", response_model=JobTagsResponse)
async def assign_tags_to_job(
    job_id: str,
    assignment: TagAssignment,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Assign tags to a job."""
    # Validate tag_ids (allow empty to clear all tags)
    tag_ids = assignment.tag_ids if assignment.tag_ids is not None else []
    if not isinstance(tag_ids, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tag_ids must be a list",
        )
    if not all(isinstance(tid, int) for tid in tag_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tag_ids must be a list of integers",
        )

    # Get the job
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.user_id == current_user.id)
        .options(selectinload(Job.tags))
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Get the tags
    if not tag_ids:
        job.tags.clear()
        await db.commit()
        return JobTagsResponse(job_id=job.id, tags=[])

    stmt = select(Tag).where(Tag.id.in_(tag_ids))
    stmt = stmt.where((Tag.owner_user_id.is_(None)) | (Tag.owner_user_id == current_user.id))
    result = await db.execute(stmt)
    tags = result.scalars().all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="One or more tags not found"
        )

    # Assign tags (idempotent: clear then add)
    job.tags.clear()
    for tag in tags:
        job.tags.append(tag)
    await db.commit()

    return JobTagsResponse(
        job_id=job.id,
        tags=[TagBasic(id=tag.id, name=tag.name, color=tag.color) for tag in tags],
    )


@job_tags_router.delete("/jobs/{job_id}/tags/{tag_id}", response_model=TagRemoveResponse)
async def remove_tag_from_job(
    job_id: str,
    tag_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Remove a tag from a job."""
    # Get the job with tags
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.user_id == current_user.id)
        .options(selectinload(Job.tags))
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Find the tag in the job's tags
    tag_to_remove = None
    for tag in job.tags:
        if tag.id == tag_id:
            tag_to_remove = tag
            break

    if not tag_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not assigned to this job"
        )

    job.tags.remove(tag_to_remove)
    await db.commit()

    return TagRemoveResponse(message="Tag removed from job", job_id=job_id, tag_id=tag_id)
