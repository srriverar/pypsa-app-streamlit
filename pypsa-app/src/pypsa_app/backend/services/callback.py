"""Callback helpers for notifying external systems of run status changes."""

import logging

import httpx

from pypsa_app.backend.models import Run

logger = logging.getLogger(__name__)


def _build_payload(run: Run) -> dict:
    return {"run_id": str(run.job_id), "status": run.status.value}


def post_callback_sync(url: str, payload: dict) -> None:
    """POST to a callback URL (blocking)."""
    try:
        httpx.post(url, json=payload, timeout=5.0, follow_redirects=False)
    except Exception:
        logger.warning(
            "Callback failed for run %s to %s",
            payload.get("run_id"),
            url,
            exc_info=True,
        )


def fire_callback_sync(run: Run) -> None:
    """POST to the run's callback URL (blocking)."""
    if not run.callback_url:
        return
    post_callback_sync(str(run.callback_url), _build_payload(run))


async def fire_callback_async(url: str, payload: dict) -> None:
    """POST to a callback URL (async). Used by the background sync loop."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=5.0, follow_redirects=False)
    except Exception:
        logger.warning(
            "Callback failed for run %s to %s",
            payload.get("run_id"),
            url,
            exc_info=True,
        )
