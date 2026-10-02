"""Admin Snakedispatch-backend management + backend-side user assignments."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from pypsa_app.backend.api.deps import (
    get_backend,
    get_db,
    get_user,
    require_permission,
)
from pypsa_app.backend.models import Permission, SnakedispatchBackend, User
from pypsa_app.backend.schemas.auth import UserResponse
from pypsa_app.backend.schemas.backend import BackendResponse, UserBackendAssign
from pypsa_app.backend.schemas.common import MessageResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/backends", response_model=list[BackendResponse])
def list_backends(
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission(Permission.SYSTEM_MANAGE)),
) -> list[SnakedispatchBackend]:
    """List all registered Snakedispatch backends."""
    return db.scalars(
        select(SnakedispatchBackend).order_by(SnakedispatchBackend.name)
    ).all()


@router.get("/backends/{backend_id}", response_model=BackendResponse)
def get_backend_detail(
    backend: SnakedispatchBackend = Depends(get_backend),
) -> SnakedispatchBackend:
    """Get a single backend by ID."""
    return backend


@router.get("/backends/{backend_id}/users", response_model=list[UserResponse])
def list_backend_users(
    backend: SnakedispatchBackend = Depends(get_backend),
) -> list[User]:
    """List users assigned to a backend."""
    return backend.users


@router.post("/backends/{backend_id}/users", response_model=MessageResponse)
def assign_user_to_backend(
    body: UserBackendAssign,
    db: Session = Depends(get_db),
    backend: SnakedispatchBackend = Depends(get_backend),
) -> dict:
    """Assign a user to a backend."""
    user = db.get(User, body.user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if user in backend.users:
        raise HTTPException(409, "User already assigned to this backend")

    backend.users.append(user)
    db.commit()
    logger.info(
        "User %s assigned to backend %s",
        user.username,
        backend.name,
    )
    return {"message": f"User {user.username} assigned to backend {backend.name}"}


@router.delete("/backends/{backend_id}/users/{user_id}", response_model=MessageResponse)
def unassign_user_from_backend(
    user: User = Depends(get_user),
    backend: SnakedispatchBackend = Depends(get_backend),
    db: Session = Depends(get_db),
) -> dict:
    """Remove a user from a backend."""
    if user not in backend.users:
        raise HTTPException(404, "User is not assigned to this backend")

    backend.users.remove(user)
    db.commit()
    logger.info(
        "User %s unassigned from backend %s",
        user.username,
        backend.name,
    )
    return {"message": f"User {user.username} removed from backend {backend.name}"}
