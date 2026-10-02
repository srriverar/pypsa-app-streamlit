"""Admin run management routes (bypasses owner/visibility rules)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from pypsa_app.backend.api.deps import get_db, require_permission
from pypsa_app.backend.api.pagination import (
    FilteredListParams,
    apply_pagination,
    list_meta,
)
from pypsa_app.backend.filters import (
    FieldMap,
    FieldSpec,
    apply_filter_to_query,
    enum_coercer,
    name_to_id,
)
from pypsa_app.backend.models import Permission, Run, User, Visibility
from pypsa_app.backend.schemas.common import MessageResponse
from pypsa_app.backend.schemas.run import (
    RunAdminUpdate,
    RunListResponse,
    RunResponse,
    RunSummary,
)
from pypsa_app.backend.services.backend_registry import backend_registry

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_admin_run_field_map(db: Session) -> FieldMap:
    return {
        "visibility": FieldSpec(Run.visibility, enum_coercer(Visibility)),
        "owner": FieldSpec(Run.user_id, name_to_id(db, User, "username", "user")),
    }


@router.get("/runs", response_model=RunListResponse)
def list_all_runs(
    filters: FilteredListParams = Depends(),
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission(Permission.RUNS_MANAGE_ALL)),
) -> RunListResponse:
    """List ALL runs (admin only) - bypasses normal visibility rules"""
    query = select(Run).options(joinedload(Run.owner), joinedload(Run.backend))

    query = apply_filter_to_query(
        query,
        filters.filter_q,
        _build_admin_run_field_map(db),
        text_fields=(Run.workflow, Run.configfile),
    )

    runs_query, total = apply_pagination(
        query,
        Run,
        filters,
        session=db,
        allowed_sort_fields={"created_at", "status", "workflow"},
    )
    runs = db.scalars(runs_query).all()

    return RunListResponse(
        data=[RunSummary.model_validate(r) for r in runs],
        meta=list_meta(total, filters, len(runs)),
    )


@router.patch("/runs/{run_id}", response_model=RunResponse)
def update_run_admin(
    run_id: UUID,
    body: RunAdminUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission(Permission.RUNS_MANAGE_ALL)),
) -> RunResponse:
    """Update run properties (admin only) - can change owner, visibility"""
    run = (
        db.scalars(
            select(Run)
            .options(
                joinedload(Run.owner),
                joinedload(Run.backend),
                joinedload(Run.networks),
            )
            .where(Run.job_id == run_id)
        )
        .unique()
        .first()
    )
    if not run:
        raise HTTPException(404, "Run not found")

    changes = []

    if body.user_id is not None:
        old_owner = run.owner.username
        new_owner = db.get(User, body.user_id)
        if not new_owner:
            raise HTTPException(400, "Specified owner does not exist")
        run.user_id = body.user_id
        changes.append(f"owner: {old_owner} -> {new_owner.username}")
    elif "user_id" in body.model_fields_set:
        raise HTTPException(400, "Cannot set owner to null")

    if body.visibility is not None:
        old_vis = run.visibility.value
        run.visibility = body.visibility
        changes.append(f"visibility: {old_vis} -> {body.visibility.value}")

    if changes:
        db.commit()
        db.refresh(run)
        logger.info(
            "Run updated by admin: %s - %s by %s",
            run.job_id,
            ", ".join(changes),
            admin.username,
        )

    return RunResponse.model_validate(run)


@router.delete("/runs/{run_id}", response_model=MessageResponse)
def delete_run_admin(
    run_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission(Permission.RUNS_MANAGE_ALL)),
) -> dict:
    """Delete any run (admin only)"""
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")

    # Clean up remote job on the execution backend
    client = backend_registry.get_client(run.backend_id)
    if client:
        try:
            client.delete_job(str(run_id))
        except Exception:
            logger.warning("Remote cleanup failed for run %s", run_id, exc_info=True)

    db.delete(run)
    db.commit()
    logger.info("Run deleted by admin: %s by %s", run_id, admin.username)
    return {"message": "Run removed"}
