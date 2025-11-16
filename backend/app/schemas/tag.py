"""Tag schemas for request/response validation."""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TagBase(BaseModel):
    """Base tag schema."""

    name: str = Field(..., min_length=1, max_length=50)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagCreate(TagBase):
    """Schema for creating a tag."""

    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag."""

    name: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("name", "color")
    @classmethod
    def check_at_least_one_field(cls, v, info):
        """Ensure at least one field is provided."""
        return v


class TagResponse(TagBase):
    """Schema for tag response."""

    id: int
    job_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    """Schema for list of tags."""

    total: int
    items: list[TagResponse]


class TagAssignment(BaseModel):
    """Schema for assigning tags to a job."""

    tag_ids: list[int] = Field(..., min_length=1)


class TagBasic(BaseModel):
    """Basic tag info for nested responses."""

    id: int
    name: str
    color: str | None

    model_config = ConfigDict(from_attributes=True)


class JobTagsResponse(BaseModel):
    """Schema for job tags response."""

    job_id: str
    tags: list[TagBasic]


class TagDeleteResponse(BaseModel):
    """Schema for tag deletion response."""

    message: str
    id: int
    jobs_affected: int


class TagRemoveResponse(BaseModel):
    """Schema for removing tag from job."""

    message: str
    job_id: str
    tag_id: int
