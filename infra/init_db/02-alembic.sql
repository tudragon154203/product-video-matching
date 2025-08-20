-- Create alembic_version table for migration tracking
-- This ensures Alembic can properly track migration state
-- Run this after 01-init.sql during database initialization

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Set the initial migration version based on current database state
-- The database schema currently matches migration 003
-- (has job_id column but no marketplace/price columns)

INSERT INTO alembic_version (version_num)
VALUES ('002')
ON CONFLICT (version_num) DO NOTHING;

-- Verify the table was created and populated
SELECT 'alembic_version table created and initialized' as status;
SELECT version_num FROM alembic_version;