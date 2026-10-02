"""Add visibility column to runs table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename the enum type from 'network_visibility' to 'visibility' if it
    # exists under the old name (databases created before this was shared
    # between networks and runs). Only needed for PostgreSQL — SQLite has no
    # named enum types.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        has_old = bind.execute(
            sa.text("SELECT 1 FROM pg_type WHERE typname = 'network_visibility'")
        ).scalar()
        if has_old:
            bind.execute(sa.text("ALTER TYPE network_visibility RENAME TO visibility"))

    # Reuse the 'visibility' enum type from the networks table
    op.add_column(
        "runs",
        sa.Column(
            "visibility",
            sa.Enum(
                "public",
                "private",
                name="visibility",
                native_enum=True,
                create_type=False,
            ),
            nullable=False,
            server_default="private",
        ),
    )
    op.create_index(op.f("ix_runs_visibility"), "runs", ["visibility"])


def downgrade() -> None:
    op.drop_index(op.f("ix_runs_visibility"), table_name="runs")
    op.drop_column("runs", "visibility")

    # Restore the old enum name for PostgreSQL, but only if the upgrade
    # actually renamed it (i.e. it was 'network_visibility' before).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        has_new = bind.execute(
            sa.text("SELECT 1 FROM pg_type WHERE typname = 'visibility'")
        ).scalar()
        if has_new:
            bind.execute(sa.text("ALTER TYPE visibility RENAME TO network_visibility"))
