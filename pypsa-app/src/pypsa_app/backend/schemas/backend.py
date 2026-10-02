"""Backend schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserBackendAssign(BaseModel):
    """Request body for assigning a user to a backend."""

    user_id: uuid.UUID


class BackendAssign(BaseModel):
    """Request body for assigning a backend to a user."""

    backend_id: uuid.UUID


class BackendPublicResponse(BaseModel):
    """Backend info visible to regular users (no internal URL)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool


class BackendResponse(BackendPublicResponse):
    """Full backend info for admin endpoints."""

    url: str
    created_at: datetime
    updated_at: datetime | None = None
