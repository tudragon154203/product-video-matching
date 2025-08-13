-- Update jobs table schema according to Sprint 2 specification
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS query TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS queries JSONB;
ALTER TABLE jobs ALTER COLUMN phase SET DEFAULT 'collection';

-- Create index on created_at for better performance
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at DESC);