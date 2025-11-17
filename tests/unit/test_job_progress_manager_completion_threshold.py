"""Tests for JobProgressManager completion threshold logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from vision_common import JobProgressManager
from vision_common.job_progress_manager.base_manager import BaseJobProgressManager


def _build_mock_broker():
    broker = MagicMock()
    broker.publish_event = AsyncMock()
    return broker


@pytest.mark.asyncio
async def test_update_job_progress_triggers_completion_at_threshold():
    """Ensure automatic completion fires once the threshold is met."""
    broker = _build_mock_broker()

    with patch(
        "vision_common._job_progress_manager._get_completion_threshold_percentage",
        return_value=80,
    ):
        manager = JobProgressManager(broker)

    manager.completion_publisher.publish_completion_event_with_count = AsyncMock()

    await manager.update_job_progress(
        job_id="job-threshold",
        asset_type="image",
        expected_count=10,
        increment=8,
        event_type_prefix="embeddings",
    )

    manager.completion_publisher.publish_completion_event_with_count.assert_called_once_with(
        "job-threshold", "image", 10, 8, "embeddings"
    )


@pytest.mark.asyncio
async def test_update_job_progress_does_not_trigger_before_threshold():
    """Verify completion is not triggered until the threshold is satisfied."""
    broker = _build_mock_broker()

    with patch(
        "vision_common._job_progress_manager._get_completion_threshold_percentage",
        return_value=90,
    ):
        manager = JobProgressManager(broker)

    manager.completion_publisher.publish_completion_event_with_count = AsyncMock()

    await manager.update_job_progress(
        job_id="job-threshold-pending",
        asset_type="video",
        expected_count=20,
        increment=17,
        event_type_prefix="segmentation",
    )

    manager.completion_publisher.publish_completion_event_with_count.assert_not_called()


@pytest.mark.asyncio
async def test_update_expected_rechecks_threshold_before_emitting():
    """Ensure recheck logic honors the completion threshold."""
    broker = _build_mock_broker()

    with patch(
        "vision_common._job_progress_manager._get_completion_threshold_percentage",
        return_value=75,
    ):
        manager = JobProgressManager(broker)

    manager.completion_publisher.publish_completion_event_with_count = AsyncMock()

    key = "job-recheck:image:embeddings"
    manager.base_manager.job_tracking[key] = {"expected": 1_000_000, "done": 70}

    completion = await manager.update_expected_and_recheck_completion(
        job_id="job-recheck",
        asset_type="image",
        real_expected=100,
        event_type_prefix="embeddings",
    )
    assert completion is False
    manager.completion_publisher.publish_completion_event_with_count.assert_not_called()

    manager.base_manager.job_tracking[key]["done"] = 80
    completion = await manager.update_expected_and_recheck_completion(
        job_id="job-recheck",
        asset_type="image",
        real_expected=100,
        event_type_prefix="embeddings",
    )
    assert completion is True
    manager.completion_publisher.publish_completion_event_with_count.assert_called_once_with(
        "job-recheck", "image", 100, 80, "embeddings"
    )


def test_base_manager_respects_completion_threshold():
    """Verify BaseJobProgressManager compares against the configured ratio."""
    broker = MagicMock()
    manager = BaseJobProgressManager(broker, completion_threshold=0.9)

    assert manager._has_reached_completion(done=9, expected=10) is True
    assert manager._has_reached_completion(done=8, expected=10) is False


def test_base_manager_allows_zero_expected_shortcut():
    """Zero expected assets should short-circuit to the original behaviour."""
    broker = MagicMock()
    manager = BaseJobProgressManager(broker, completion_threshold=0.9)

    assert manager._has_reached_completion(done=0, expected=0) is True
    assert manager._has_reached_completion(done=-1, expected=0) is False
