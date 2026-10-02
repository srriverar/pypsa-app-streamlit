"""Admin routes (users, networks, runs, backends).

Combines per-resource sub-routers into a single `router` that
`main.py` mounts under `/api/v1/admin`.
"""

from fastapi import APIRouter

from pypsa_app.backend.api.routes.admin import (
    backends,
    meta,
    networks,
    runs,
    users,
)

router = APIRouter()
router.include_router(meta.router)
router.include_router(users.router)
router.include_router(networks.router)
router.include_router(runs.router)
router.include_router(backends.router)

__all__ = ["router"]
