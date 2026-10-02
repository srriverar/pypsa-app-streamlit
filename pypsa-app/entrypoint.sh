#!/bin/bash
set -e

# Fix /data ownership for bind mounts created by Docker as root
mkdir -p /data
chown -R appuser:appuser /data

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    gosu appuser alembic upgrade head
fi

# Use tini as PID 1 to clean up zombie processes (e.g. docker health checks)
exec tini -- gosu appuser "$@"
