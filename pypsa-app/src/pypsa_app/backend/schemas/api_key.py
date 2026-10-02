"""API key schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from pypsa_app.backend.schemas.auth import UserPublicResponse


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    expires_in_days: int = Field(..., gt=0, le=365)
    user_id: UUID = Field(..., description="Bot user to link this API key to")


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    owner: UserPublicResponse
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    key: str | None = None

    model_config = {"from_attributes": True}
