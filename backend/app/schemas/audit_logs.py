"""Schemas for audit log responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AuditLogItem(BaseModel):
    id: int
    actor_user_id: Optional[int]
    actor_email: Optional[str]
    action: str
    target_type: Optional[str]
    target_id: Optional[str]
    metadata: Optional[dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    total: int
    items: list[AuditLogItem]
