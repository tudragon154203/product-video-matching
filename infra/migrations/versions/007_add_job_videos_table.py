"""Create job_videos association table and drop legacy videos.job_id

Revision ID: 007
Revises: 006
Create Date: 2025-11-15
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS job_videos (
            job_id VARCHAR(255) NOT NULL,
            video_id VARCHAR(255) NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
            platform VARCHAR(50) NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (job_id, video_id)
        );
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_videos_video_id ON job_videos(video_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_videos_job_platform ON job_videos(job_id, platform);"
    )

    # Backfill associations for existing records that already stored job_id on videos
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'videos' AND column_name = 'job_id'
            ) THEN
                INSERT INTO job_videos (job_id, video_id, platform, assigned_at)
                SELECT v.job_id, v.video_id, v.platform, COALESCE(v.created_at, NOW())
                FROM videos v
                WHERE v.job_id IS NOT NULL
                ON CONFLICT (job_id, video_id) DO NOTHING;
            END IF;
        END$$;
        """
    )

    # Drop legacy indexes/column now that job_videos owns the association
    op.execute("DROP INDEX IF EXISTS idx_videos_job_platform;")
    op.execute("DROP INDEX IF EXISTS idx_videos_platform_job_id;")
    op.execute("DROP INDEX IF EXISTS idx_videos_job_id;")
    op.execute("ALTER TABLE videos DROP COLUMN IF EXISTS job_id;")


def downgrade() -> None:
    op.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS job_id VARCHAR(255);")
    op.execute(
        """
        UPDATE videos v
        SET job_id = sub.job_id
        FROM (
            SELECT video_id, MIN(job_id) AS job_id
            FROM job_videos
            GROUP BY video_id
        ) sub
        WHERE v.video_id = sub.video_id;
        """
    )
    op.execute("DROP TABLE IF EXISTS job_videos;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_videos_job_id ON videos(job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_videos_platform_job_id ON videos(platform, job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_videos_job_platform ON videos(job_id, platform);")
