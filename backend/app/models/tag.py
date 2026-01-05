"""Tag model and job-tag association table."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base

# Junction table for many-to-many relationship
job_tags = Table(
    "job_tags",
    Base.metadata,
    Column("job_id", String(36), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    """Tag table for job organization."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    color = Column(String(7), nullable=True)  # hex color
    owner_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    jobs = relationship("Job", secondary=job_tags, back_populates="tags")
    owner = relationship("User", back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}', owner={self.owner_user_id})>"
