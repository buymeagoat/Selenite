"""Audit log model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    """Audit trail for admin and auth actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(100), nullable=True)
    target_id = Column(String(100), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    actor = relationship("User", backref="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', actor={self.actor_user_id})>"
