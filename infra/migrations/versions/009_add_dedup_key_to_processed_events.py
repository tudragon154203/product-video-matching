"""Add dedup_key to processed_events for evidence builder idempotency

Revision ID: 009
Revises: 008
Create Date: 2025-11-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get connection to execute raw SQL with exception handling
    conn = op.get_bind()
    
    # Drop primary key constraint on event_id
    conn.execute(sa.text("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE processed_events DROP CONSTRAINT processed_events_pkey;
            EXCEPTION 
                WHEN undefined_object THEN NULL;
            END;
        END $$;
    """))
    
    # Make event_id nullable
    conn.execute(sa.text("""
        ALTER TABLE processed_events ALTER COLUMN event_id DROP NOT NULL;
    """))
    
    # Add dedup_key column if it doesn't exist
    conn.execute(sa.text("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE processed_events ADD COLUMN dedup_key VARCHAR(255);
            EXCEPTION 
                WHEN duplicate_column THEN NULL;
            END;
        END $$;
    """))
    
    # Add processed_at column if it doesn't exist
    conn.execute(sa.text("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE processed_events ADD COLUMN processed_at TIMESTAMP DEFAULT NOW() NOT NULL;
            EXCEPTION 
                WHEN duplicate_column THEN NULL;
            END;
        END $$;
    """))

    # Create unique constraint if it doesn't exist
    conn.execute(sa.text("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE processed_events 
                ADD CONSTRAINT uq_processed_events_type_dedup 
                UNIQUE (event_type, dedup_key);
            EXCEPTION 
                WHEN duplicate_table THEN NULL;
            END;
        END $$;
    """))

    # Create index if it doesn't exist
    conn.execute(sa.text("""
        DO $$ 
        BEGIN 
            BEGIN
                CREATE INDEX ix_processed_events_type_dedup 
                ON processed_events (event_type, dedup_key);
            EXCEPTION 
                WHEN duplicate_table THEN NULL;
            END;
        END $$;
    """))
    
    # Create partial unique index on event_id for backward compatibility
    conn.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS processed_events_event_id_idx 
        ON processed_events(event_id) WHERE event_id IS NOT NULL;
    """))


def downgrade() -> None:
    # Drop partial index
    op.execute('DROP INDEX IF EXISTS processed_events_event_id_idx')
    
    # Drop index and constraint
    op.drop_index('ix_processed_events_type_dedup', table_name='processed_events')
    op.drop_constraint('uq_processed_events_type_dedup', 'processed_events', type_='unique')

    # Drop columns
    op.drop_column('processed_events', 'processed_at')
    op.drop_column('processed_events', 'dedup_key')
    
    # Restore event_id as NOT NULL
    op.alter_column('processed_events', 'event_id', nullable=False)
    
    # Restore primary key
    op.create_primary_key('processed_events_pkey', 'processed_events', ['event_id'])
