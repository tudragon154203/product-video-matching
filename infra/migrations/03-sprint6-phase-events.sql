-- Add table for tracking phase events
CREATE TABLE IF NOT EXISTS phase_events (
    event_id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_phase_events_job_id ON phase_events(job_id);
CREATE INDEX IF NOT EXISTS idx_phase_events_name ON phase_events(name);

-- Add phase column to jobs table if it doesn't exist
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS phase VARCHAR(50) NOT NULL;