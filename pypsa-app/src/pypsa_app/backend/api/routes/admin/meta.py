"""Admin meta endpoints (permission catalogue)."""

from fastapi import APIRouter, Depends

from pypsa_app.backend.api.deps import require_permission
from pypsa_app.backend.models import Permission, User
from pypsa_app.backend.permissions import get_role_permissions

router = APIRouter()


@router.get("/permissions")
def get_permissions(
    admin: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> dict:
    """Get all available permissions and role mappings"""
    return {
        "permissions": [p.value for p in Permission],
        "role_permissions": {
            role.value: [p.value for p in perms]
            for role, perms in get_role_permissions().items()
        },
    }
