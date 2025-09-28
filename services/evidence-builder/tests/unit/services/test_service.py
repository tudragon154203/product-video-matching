"""Tests for the evidence builder service layer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.service import EvidenceBuilderService

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_db():
    return AsyncMock()


@pytest.fixture()
def mock_broker():
    return AsyncMock()


@pytest.fixture()
def service(mock_db, mock_broker):
    return EvidenceBuilderService(mock_db, mock_broker, "./data")


def _setup_match_record_manager(image_info=None, frame_info=None):
    return SimpleNamespace(
        get_image_info=AsyncMock(return_value=image_info),
        get_frame_info=AsyncMock(return_value=frame_info),
        update_match_record_and_log=AsyncMock(),
    )


def _setup_evidence_publisher():
    return SimpleNamespace(
        publish_evidence_completion_if_needed=AsyncMock(),
        handle_matchings_completed=AsyncMock(),
    )


def test_service_initialization(service):
    """Service should initialize its collaborators."""
    assert service.db is not None
    assert service.broker is not None
    assert service.evidence_generator is not None
    assert service.match_record_manager is not None
    assert service.evidence_publisher is not None


@pytest.mark.asyncio
async def test_handle_match_result_generates_evidence(service):
    """Generate evidence and update the record when assets exist."""
    event_data = {
        "job_id": "job123",
        "product_id": "product456",
        "video_id": "video789",
        "best_pair": {"img_id": "img123", "frame_id": "frame456"},
        "score": 0.92,
        "ts": 10.5,
    }

    image_info = {"local_path": "/tmp/product.jpg", "kp_blob_path": None}
    frame_info = {"local_path": "/tmp/frame.jpg", "kp_blob_path": None}

    service.match_record_manager = _setup_match_record_manager(
        image_info=image_info,
        frame_info=frame_info,
    )
    service.evidence_generator = MagicMock()
    service.evidence_generator.create_evidence.return_value = \
        "/tmp/evidence.jpg"
    service.evidence_publisher = _setup_evidence_publisher()

    await service.handle_match_result(event_data)

    service.evidence_generator.create_evidence.assert_called_once()
    service.match_record_manager.update_match_record_and_log.assert_called_once_with(
        "job123",
        "product456",
        "video789",
        "/tmp/evidence.jpg",
    )
    service.evidence_publisher.publish_evidence_completion_if_needed.assert_called_once_with(
        "job123"
    )


@pytest.mark.asyncio
async def test_handle_match_result_missing_assets(service):
    """Do not generate evidence when media assets are missing."""
    event_data = {
        "job_id": "job123",
        "product_id": "product456",
        "video_id": "video789",
        "best_pair": {"img_id": "img123", "frame_id": "frame456"},
        "score": 0.92,
        "ts": 10.5,
    }

    service.match_record_manager = _setup_match_record_manager(
        image_info=None,
        frame_info=None,
    )
    service.evidence_generator = MagicMock()
    service.evidence_publisher = _setup_evidence_publisher()

    await service.handle_match_result(event_data)

    service.evidence_generator.create_evidence.assert_not_called()
    service.match_record_manager.update_match_record_and_log.assert_not_called()
    service.evidence_publisher.publish_evidence_completion_if_needed.assert_not_called()


@pytest.mark.asyncio
async def test_handle_matchings_completed_delegates(service):
    """Delegate matchings completion handling to the publisher."""
    event_data = {"job_id": "job123"}
    service.evidence_publisher = _setup_evidence_publisher()

    await service.handle_matchings_completed(event_data)

    service.evidence_publisher.handle_matchings_completed.assert_called_once_with(
        event_data
    )
