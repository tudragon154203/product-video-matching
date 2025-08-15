"""Create/initialize alembic_version (translated from 02-alembic.sql)

Revision ID: 002
Revises: 001
Create Date: 2025-08-16
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create alembic_version table if missing (defensive)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        );
        """
    )

    # Initialize version to '001' if empty
    op.execute(
        """
        INSERT INTO alembic_version (version_num)
        SELECT '002'
        WHERE NOT EXISTS (SELECT 1 FROM alembic_version);
        """
    )

    # Optional: visibility check (no-op for Alembic runtime)
    # op.execute("SELECT version_num FROM alembic_version;")


def downgrade() -> None:
    # Usually we do NOT drop alembic_version, but to mirror the .sql intent we keep a no-op.
    # If you really want to drop it, uncomment the next line (not recommended):
    # op.execute("DROP TABLE IF EXISTS alembic_version;")
    pass
