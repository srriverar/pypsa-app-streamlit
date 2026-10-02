"""Error sanitization for user-facing task responses."""

import httpx
from sqlalchemy.exc import SQLAlchemyError


def sanitize_task_error(exc: Exception) -> str:
    """Return a safe error message for the frontend."""
    # Replace DB/filesystem internals with generic messages
    if isinstance(exc, SQLAlchemyError):
        return "A database error occurred"
    if isinstance(exc, OSError):
        return "A file system error occurred"
    # ValueError and HTTP status errors carry intentionally user-facing text
    if isinstance(exc, (ValueError, httpx.HTTPStatusError)):
        return str(exc)
    return "An unexpected error occurred"
