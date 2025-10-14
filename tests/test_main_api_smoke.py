#!/usr/bin/env python3
"""
Focused smoke test for main-api to identify which microservice is blocking
jobs from progressing past the feature extraction phase.
"""
import asyncio
import httpx
import time
import os
import sys
import json

# Add libs to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))

from common_py.logging_config import configure_logging

logger = configure_logging("main-api-smoke-test")

# Service URLs
MAIN_API_URL = "http://localhost:8888"


async def run_main_api_smoke_test():
    """Run focused smoke test on main-api to monitor job progression through phases"""
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            logger.info("Starting main-api smoke test...")

            # Step 1: Check main-api health
            await check_main_api_health(client)

            # Step 2: Start a minimal job for faster processing
            job_id = await start_minimal_job(client)

            # Step 3: Monitor job progression through phases with detailed logging
            await monitor_job_phases_detailed(client, job_id)

            logger.info("Main-api smoke test completed!")

    except Exception as e:
        logger.error(f"Smoke test failed: {str(e)}")
        raise


async def check_main_api_health(client):
    """Check main-api health and get system status"""
    logger.info("Checking main-api health...")

    try:
        response = await client.get(f"{MAIN_API_URL}/health")
        response.raise_for_status()
        health_data = response.json()
        logger.info(f"Main API health: {health_data}")

        # Get additional stats
        response = await client.get(f"{MAIN_API_URL}/stats")
        response.raise_for_status()
        stats = response.json()
        logger.info(f"System stats: {json.dumps(stats, indent=2)}")

    except Exception as e:
        logger.error(f"Main API health check failed: {str(e)}")
        raise


async def start_minimal_job(client):
    """Start a minimal job for faster processing"""
    logger.info("Starting minimal job...")

    # Use minimal parameters for faster processing
    job_request = {
        "query": "laptop",
        "top_amz": 1,
        "top_ebay": 1,
        "platforms": ["youtube"],  # Only one platform
        "recency_days": 365  # Shorter recency
    }

    response = await client.post(f"{MAIN_API_URL}/start-job", json=job_request)
    response.raise_for_status()

    job_data = response.json()
    job_id = job_data["job_id"]

    logger.info(f"Job started successfully (job_id: {job_id})")
    return job_id


async def monitor_job_phases_detailed(client, job_id, max_wait_time=180):
    """Monitor job progression through phases with detailed logging"""
    logger.info(f"Monitoring job phases in detail... (job_id: {job_id})")

    start_time = time.time()
    last_phase = None
    phase_start_time = time.time()
    stuck_threshold = 120  # Consider stuck if in same phase for 60 seconds

    while time.time() - start_time < max_wait_time:
        try:
            # Get job status
            response = await client.get(f"{MAIN_API_URL}/status/{job_id}")
            response.raise_for_status()

            status_data = response.json()
            current_phase = status_data["phase"]
            percent = status_data["percent"]

            # Log phase transitions
            if current_phase != last_phase:
                if last_phase is not None:
                    phase_duration = time.time() - phase_start_time
                    logger.info(f"Phase transition: {last_phase} -> {current_phase} (duration: {phase_duration:.1f}s)")
                else:
                    logger.info(f"Starting phase: {current_phase}")

                last_phase = current_phase
                phase_start_time = time.time()

            # Check for potentially stuck phases
            current_phase_duration = time.time() - phase_start_time
            if current_phase_duration > stuck_threshold and current_phase not in ["completed", "failed"]:
                logger.warning(f"Phase {current_phase} appears stuck (duration: {current_phase_duration:.1f}s)")
                await analyze_phase_blockers(client, job_id, current_phase)

            logger.info(f"Job status - Phase: {current_phase}, Progress: {percent}%, Duration: {current_phase_duration:.1f}s")

            # Terminal states
            if current_phase == "completed":
                logger.info(f"Job completed successfully! (job_id: {job_id})")
                return
            elif current_phase == "failed":
                logger.error(f"Job failed! (job_id: {job_id})")
                await get_job_error_details(client, job_id)
                return

            # Special focus on feature extraction phase
            if current_phase == "feature_extraction":
                await analyze_feature_extraction_progress(client, job_id)

            await asyncio.sleep(3)  # Check every 3 seconds

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"Job not found (job_id: {job_id})")
                raise
            else:
                logger.warning(f"Status check failed, retrying... ({str(e)})")
                await asyncio.sleep(2)

    logger.error(f"Job monitoring timeout after {max_wait_time} seconds")
    await analyze_phase_blockers(client, job_id, current_phase)


async def analyze_feature_extraction_progress(client, job_id):
    """Analyze what's happening in feature extraction phase"""
    logger.info(f"Analyzing feature extraction progress for job {job_id}")

    try:
        # Check if we can get more detailed status
        response = await client.get(f"{MAIN_API_URL}/status/{job_id}")
        status_data = response.json()

        # Log any additional status info that might help debug
        if "details" in status_data:
            logger.info(f"Feature extraction details: {status_data['details']}")

        # Check what assets this job has
        logger.info(f"Job assets would be checked here - monitoring required completion events")

    except Exception as e:
        logger.warning(f"Could not get detailed feature extraction status: {str(e)}")


async def analyze_phase_blockers(client, job_id, current_phase):
    """Analyze what might be blocking the current phase"""
    logger.warning(f"Analyzing blockers for phase: {current_phase}")

    if current_phase == "feature_extraction":
        logger.warning("FEATURE EXTRACTION PHASE BLOCKER ANALYSIS:")
        logger.warning("Checking required completion events:")
        logger.warning("  - products.collections.completed")
        logger.warning("  - videos.collections.completed")
        logger.warning("  - image.embeddings.completed")
        logger.warning("  - image.keypoints.completed")
        logger.warning("  - video.embeddings.completed")
        logger.warning("  - video.keypoints.completed")

        logger.warning("Microservices to check:")
        logger.warning("  - dropship-product-finder (product collection)")
        logger.warning("  - video-crawler (video collection)")
        logger.warning("  - vision-embedding (embeddings)")
        logger.warning("  - vision-keypoint (keypoints)")
        logger.warning("  - product-segmentor (image preprocessing)")

    elif current_phase == "collection":
        logger.warning("COLLECTION PHASE BLOCKER ANALYSIS:")
        logger.warning("Microservices to check:")
        logger.warning("  - dropship-product-finder")
        logger.warning("  - video-crawler")

    elif current_phase == "matching":
        logger.warning("MATCHING PHASE BLOCKER ANALYSIS:")
        logger.warning("Microservices to check:")
        logger.warning("  - matcher")

    elif current_phase == "evidence":
        logger.warning("EVIDENCE PHASE BLOCKER ANALYSIS:")
        logger.warning("Microservices to check:")
        logger.warning("  - evidence-builder")


async def get_job_error_details(client, job_id):
    """Get detailed error information for failed jobs"""
    try:
        response = await client.get(f"{MAIN_API_URL}/status/{job_id}")
        status_data = response.json()

        logger.error(f"Job error details: {json.dumps(status_data, indent=2)}")

    except Exception as e:
        logger.error(f"Could not get error details: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_main_api_smoke_test())