"""Add job cancellation and deletion support

Revision ID: 008
Revises: 007
Create Date: 2025-11-18
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cancellation and deletion timestamp columns to jobs table
    op.execute(
        """
        ALTER TABLE jobs
        ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP,
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
        ADD COLUMN IF NOT EXISTS cancelled_by VARCHAR(255),
        ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(255);
        """
    )

    # Add payload column to phase_events for storing metadata
    op.execute(
        """
        ALTER TABLE phase_events
        ADD COLUMN IF NOT EXISTS payload JSONB;
        """
    )

    # Add indexes for filtering cancelled/deleted jobs
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_cancelled_at ON jobs(cancelled_at) WHERE cancelled_at IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_deleted_at ON jobs(deleted_at) WHERE deleted_at IS NOT NULL;"
    )


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_jobs_cancelled_at;")
    op.execute("DROP INDEX IF EXISTS idx_jobs_deleted_at;")

    # Drop columns
    op.execute(
        """
        ALTER TABLE jobs
        DROP COLUMN IF EXISTS cancelled_at,
        DROP COLUMN IF EXISTS deleted_at,
        DROP COLUMN IF EXISTS cancelled_by,
        DROP COLUMN IF EXISTS deleted_by;
        """
    )

    op.execute(
        """
        ALTER TABLE phase_events
        DROP COLUMN IF EXISTS payload;
        """
    )
