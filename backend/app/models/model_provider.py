"""Model registry tables for model sets and entries."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ModelSet(Base):
    """Represents a logical ASR or diarizer model set managed by admins."""

    __tablename__ = "model_sets"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)  # asr | diarizer
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    abs_path = Column(String(1024), nullable=False, unique=True)

    enabled = Column(Boolean, nullable=False, default=True)
    disable_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    entries = relationship(
        "ModelEntry",
        back_populates="model_set",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def weights(self):
        """Expose ORM entries as model weights for serialization."""
        return self.entries

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return "<ModelSet id={id} name={name} type={ptype} enabled={enabled}>".format(
            id=self.id,
            name=self.name,
            ptype=self.type,
            enabled=self.enabled,
        )


class ModelEntry(Base):
    """Concrete model weight under a model set."""

    __tablename__ = "model_entries"

    id = Column(Integer, primary_key=True, index=True)
    set_id = Column(
        Integer, ForeignKey("model_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type = Column(String(20), nullable=False)  # asr | diarizer (mirrors parent set)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    abs_path = Column(String(1024), nullable=False, unique=True)

    checksum = Column(String(128), nullable=True)

    enabled = Column(Boolean, nullable=False, default=True)
    disable_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    model_set = relationship("ModelSet", back_populates="entries")

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return "<ModelEntry id={id} name={name} set={set_name} enabled={enabled}>".format(
            id=self.id,
            name=self.name,
            set_name=self.model_set.name if self.model_set else "unknown",
            enabled=self.enabled,
        )


__all__ = ["ModelSet", "ModelEntry"]
