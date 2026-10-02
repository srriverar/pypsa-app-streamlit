"""Registry mapping backend IDs to SnakedispatchClient instances."""

import logging
import uuid
from typing import NamedTuple

from pypsa_app.backend.services.run import SnakedispatchClient

logger = logging.getLogger(__name__)


class _BackendEntry(NamedTuple):
    name: str
    client: SnakedispatchClient


class BackendRegistry:
    """Maps backend_id → SnakedispatchClient.

    Uses a single dict so every mutation is a single pointer swap
    (atomic under CPython's GIL).
    """

    def __init__(self) -> None:
        self._backends: dict[uuid.UUID, _BackendEntry] = {}

    def register(self, backend_id: uuid.UUID, name: str, url: str) -> None:
        """Register or update a backend client."""
        self._backends[backend_id] = _BackendEntry(name, SnakedispatchClient(url))
        logger.info("Registered backend %s (%s) → %s", name, backend_id, url)

    def get_client(self, backend_id: uuid.UUID) -> SnakedispatchClient | None:
        """Return client for a backend, or None if not registered."""
        entry = self._backends.get(backend_id)
        return entry.client if entry else None

    def all_clients(self) -> dict[uuid.UUID, SnakedispatchClient]:
        """Return all registered clients."""
        return {bid: e.client for bid, e in self._backends.items()}

    def get_name(self, backend_id: uuid.UUID) -> str | None:
        """Return the display name for a backend."""
        entry = self._backends.get(backend_id)
        return entry.name if entry else None

    def clear(self) -> None:
        """Remove all registrations."""
        self._backends = {}


# Module-level singleton
backend_registry = BackendRegistry()
