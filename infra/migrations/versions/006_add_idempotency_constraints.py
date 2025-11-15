"""Add idempotency constraints and file hash tracking

Revision ID: 006
Revises: 005
Create Date: 2025-10-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint for videos to prevent duplicates
    op.execute(
        """
        ALTER TABLE videos
        ADD CONSTRAINT videos_unique_platform_id
        UNIQUE (video_id, platform);
        """
    )

    # Add unique constraint for frames to prevent duplicates
    op.execute(
        """
        ALTER TABLE video_frames
        ADD CONSTRAINT frames_unique_video_timestamp
        UNIQUE (video_id, ts);
        """
    )

    # Create table for tracking processed file hashes (content-level idempotency)
    op.execute(
        """
        CREATE TABLE processed_file_hashes (
            file_hash VARCHAR(64) PRIMARY KEY,
            file_path TEXT,
            processed_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    # Add indexes for performance
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'videos' AND column_name = 'job_id'
            ) THEN
                CREATE INDEX IF NOT EXISTS idx_videos_platform_job_id ON videos(platform, job_id);
                CREATE INDEX IF NOT EXISTS idx_videos_job_platform ON videos(job_id, platform);
            END IF;
        END$$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_video_frames_video_id ON video_frames(video_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_processed_file_hashes_processed_at ON processed_file_hashes(processed_at);")

    # Add helpful composite indexes for common query patterns
    op.execute("CREATE INDEX IF NOT EXISTS idx_frames_video_ts ON video_frames(video_id, ts);")


def downgrade() -> None:
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_videos_job_platform;")
    op.execute("DROP INDEX IF EXISTS idx_frames_video_ts;")
    op.execute("DROP INDEX IF EXISTS idx_videos_platform_job_id;")
    op.execute("DROP INDEX IF NOT EXISTS idx_video_frames_video_id;")
    op.execute("DROP INDEX IF NOT EXISTS idx_processed_file_hashes_processed_at;")

    # Drop constraints
    op.execute("ALTER TABLE videos DROP CONSTRAINT IF EXISTS videos_unique_platform_id;")
    op.execute("ALTER TABLE video_frames DROP CONSTRAINT IF EXISTS frames_unique_video_timestamp;")

    # Drop table
    op.execute("DROP TABLE IF EXISTS processed_file_hashes;")
