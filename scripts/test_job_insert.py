#!/usr/bin/env python3
"""
Simple test script to verify that we can insert a job into the database without the status column
"""
import asyncio
import sys
import os

# Add libs and infra to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'libs'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'infra'))

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager

# Import config directly
from config import config

logger = configure_logging("test_job_insert")

# Database connection
POSTGRES_DSN = config.POSTGRES_DSN

async def test_job_insert():
    """Test inserting a job without the status column"""
    try:
        # Connect to database
        db = DatabaseManager(POSTGRES_DSN)
        await db.connect()
        
        logger.info("Connected to database")
        
        # Insert a job without the status column
        job_id = "test_job_123"
        industry = "test pillows"
        
        await db.execute(
            "INSERT INTO jobs (job_id, industry, phase) VALUES ($1, $2, $3)",
            job_id, industry, "collection"
        )
        
        logger.info("Inserted job successfully")
        
        # Retrieve the job to verify it was inserted correctly
        job = await db.fetch_one(
            "SELECT * FROM jobs WHERE job_id = $1", job_id
        )
        
        if job is not None:
            logger.info("Job retrieved successfully", job_id=job["job_id"], industry=job["industry"], phase=job["phase"])
            print("SUCCESS: Job inserted and retrieved correctly")
        else:
            logger.error("Failed to retrieve job")
            print("ERROR: Failed to retrieve job")
        
        await db.disconnect()
        
    except Exception as e:
        logger.error("Failed to insert job", error=str(e))
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_job_insert())