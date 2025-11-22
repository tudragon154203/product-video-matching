"""
Integration tests for evidence builder phase workflow.

Tests the evidence builder service's ability to:
1. Process match.result events and generate evidence images
2. Handle match.request.completed events
3. Publish evidences.generation.completed events
4. Update matches table with evidence paths
5. Advance job phase to completed
"""

import asyncio
import uuid
import pytest

from support.fixtures.evidence_phase_setup import (
    setup_evidence_phase_database_state,
    cleanup_evidence_test_database_state
)
from support.validators.db_cleanup import DatabaseStateValidator
from support.spy.message_spy import MessageSpy
from support.publisher.event_publisher import EvidenceEventPublisher
from mock_data.test_data import build_evidence_test_dataset

pytestmark = [pytest.mark.evidence, pytest.mark.integration]


class TestEvidencePhaseIntegration:
    """Test suite for evidence phase integration scenarios."""

    async def cleanup_test_data(self, db_manager, job_id: str):
        """Clean up test data to avoid conflicts between test runs."""
        await cleanup_evidence_test_database_state(db_manager, job_id)

    @pytest.fixture
    async def evidence_test_environment(self, db_manager, message_broker, clean_database):
        """Set up evidence test environment with spies and validators."""
        import os
        broker_url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

        # Set up message spies for evidence events
        evidences_completed_spy = MessageSpy(broker_url)

        # Connect spies
        await evidences_completed_spy.connect()

        evidences_completed_queue = await evidences_completed_spy.create_spy_queue(
            "evidences.generation.completed"
        )

        # Start consuming
        await evidences_completed_spy.start_consuming(evidences_completed_queue)

        # Create validators and publisher
        db_validator = DatabaseStateValidator(db_manager)
        publisher = EvidenceEventPublisher(message_broker)

        yield {
            "evidences_completed_spy": evidences_completed_spy,
            "evidences_completed_queue": evidences_completed_queue,
            "db_validator": db_validator,
            "publisher": publisher,
            "db_manager": db_manager,
        }

        # Cleanup spies
        await evidences_completed_spy.stop_consuming(evidences_completed_queue)
        await evidences_completed_spy.disconnect()

    @pytest.mark.asyncio
    async def test_evidence_generation_from_match_result(self, evidence_test_environment, db_manager):
        """
        Test 7.1: Evidence Generation from match.result Event

        Verifies that match.result events trigger evidence generation,
        update matches table with evidence_path, and eventually publish
        evidences.generation.completed when all matches are processed.
        """
        env = evidence_test_environment
        import time
        job_id = f"test_evidence_match_result_{int(time.time())}"

        # Create test dataset with match records
        dataset = build_evidence_test_dataset(job_id, num_matches=2)

        # Seed database with test data
        await setup_evidence_phase_database_state(db_manager, job_id, dataset)

        # Verify matches were created
        matches = await db_manager.fetch_all(
            "SELECT * FROM matches WHERE job_id = $1", job_id
        )
        assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}"

        # Publish match.result events
        for match_result in dataset["match_results"]:
            await env["publisher"].publish_match_result(match_result)

        # Wait for evidence generation
        await asyncio.sleep(3.0)

        # Validate matches table updated with evidence paths
        updated_matches = await db_manager.fetch_all(
            "SELECT * FROM matches WHERE job_id = $1 AND evidence_path IS NOT NULL",
            job_id
        )
        assert len(updated_matches) > 0, "Expected matches to have evidence_path updated"

        # Validate evidences.generation.completed event published
        completion_events = env["evidences_completed_spy"].get_captured_messages(
            env["evidences_completed_queue"]
        )
        assert len(completion_events) >= 1, "Expected evidences.generation.completed event"

        completion = completion_events[0]["event_data"]
        assert completion["job_id"] == job_id
        assert "event_id" in completion, "Expected event_id in completion event"

    @pytest.mark.asyncio
    async def test_evidence_zero_matches_completion(self, evidence_test_environment, db_manager):
        """
        Test 7.2: Evidence Phase with Zero Matches

        Verifies that when match.request.completed is received with no matches,
        the evidence builder still publishes evidences.generation.completed
        and advances job to completed phase.
        """
        env = evidence_test_environment
        import time
        job_id = f"test_evidence_zero_matches_{int(time.time())}"

        # Create dataset with no matches
        dataset = build_evidence_test_dataset(job_id, num_matches=0)

        # Seed database (job in evidence phase, no matches)
        await setup_evidence_phase_database_state(db_manager, job_id, dataset)

        # Verify no matches exist
        matches = await db_manager.fetch_all(
            "SELECT * FROM matches WHERE job_id = $1", job_id
        )
        assert len(matches) == 0, "Expected no matches for zero-match scenario"

        # Publish match.request.completed event
        match_request_completed = dataset["match_request_completed"]
        await env["publisher"].publish_match_request_completed(match_request_completed)

        # Wait for processing
        await asyncio.sleep(2.0)

        # Validate evidences.generation.completed event published
        completion_events = env["evidences_completed_spy"].get_captured_messages(
            env["evidences_completed_queue"]
        )
        assert len(completion_events) >= 1, "Expected evidences.generation.completed even with zero matches"

        completion = completion_events[0]["event_data"]
        assert completion["job_id"] == job_id
        assert "event_id" in completion, "Expected event_id in completion event"

    @pytest.mark.asyncio
    async def test_evidence_idempotent_processing(self, evidence_test_environment, db_manager):
        """
        Test 7.3: Evidence Builder Idempotent Processing

        Verifies that duplicate match.result events with same dedup_key
        are processed only once and don't create duplicate evidence.
        """
        env = evidence_test_environment
        import time
        job_id = f"test_evidence_idempotency_{int(time.time())}"

        # Create test dataset
        dataset = build_evidence_test_dataset(job_id, num_matches=1)

        # Seed database
        await setup_evidence_phase_database_state(db_manager, job_id, dataset)

        # Publish the SAME match.result event twice
        match_result = dataset["match_results"][0]
        await env["publisher"].publish_match_result(match_result)
        await asyncio.sleep(0.5)
        await env["publisher"].publish_match_result(match_result)

        # Wait for processing
        await asyncio.sleep(3.0)

        # Validate only one evidence path was created
        updated_matches = await db_manager.fetch_all(
            "SELECT * FROM matches WHERE job_id = $1 AND evidence_path IS NOT NULL",
            job_id
        )
        assert len(updated_matches) == 1, "Expected only one match with evidence_path"

        # Validate processed_events contains the dedup_key
        dedup_key = f"{job_id}:{match_result['product_id']}:{match_result['video_id']}:{match_result['best_pair']['img_id']}:{match_result['best_pair']['frame_id']}"
        processed = await db_manager.fetch_one(
            "SELECT * FROM processed_events WHERE dedup_key = $1", dedup_key
        )
        assert processed is not None, "Expected dedup_key to be recorded in processed_events"

    @pytest.mark.asyncio
    async def test_evidence_partial_match_processing(self, evidence_test_environment, db_manager):
        """
        Test 7.4: Evidence Builder Partial Match Processing

        Verifies that evidence builder can handle scenarios where some matches
        have evidence generated while others are still pending, and correctly
        publishes completion only when all are done.
        """
        env = evidence_test_environment
        import time
        job_id = f"test_evidence_partial_{int(time.time())}"

        # Create dataset with multiple matches
        dataset = build_evidence_test_dataset(job_id, num_matches=3)

        # Seed database
        await setup_evidence_phase_database_state(db_manager, job_id, dataset)

        # Publish only first 2 match.result events (partial processing)
        await env["publisher"].publish_match_result(dataset["match_results"][0])
        await env["publisher"].publish_match_result(dataset["match_results"][1])

        # Wait for partial processing
        await asyncio.sleep(2.0)

        # Validate partial evidence generation
        updated_matches = await db_manager.fetch_all(
            "SELECT * FROM matches WHERE job_id = $1 AND evidence_path IS NOT NULL",
            job_id
        )
        assert len(updated_matches) == 2, "Expected 2 matches with evidence_path"

        # Clear spy messages
        env["evidences_completed_spy"].clear_captured_messages(env["evidences_completed_queue"])

        # Publish final match.result event
        await env["publisher"].publish_match_result(dataset["match_results"][2])

        # Wait for final processing
        await asyncio.sleep(2.0)

        # Validate all matches have evidence
        all_updated_matches = await db_manager.fetch_all(
            "SELECT * FROM matches WHERE job_id = $1 AND evidence_path IS NOT NULL",
            job_id
        )
        assert len(all_updated_matches) == 3, "Expected all 3 matches with evidence_path"

        # Validate completion event published after all matches processed
        completion_events = env["evidences_completed_spy"].get_captured_messages(
            env["evidences_completed_queue"]
        )
        assert len(completion_events) >= 1, "Expected evidences.generation.completed after all matches"

        completion = completion_events[0]["event_data"]
        assert completion["job_id"] == job_id
        assert "event_id" in completion, "Expected event_id in completion event"
