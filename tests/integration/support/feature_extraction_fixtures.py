"""
Feature Extraction Fixtures
Pytest fixtures for feature extraction phase integration tests.
"""
import os
import sys
from pathlib import Path

# Early sys.path setup to resolve project modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LIBS_DIR = PROJECT_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"
INFRA_DIR = PROJECT_ROOT / "infra"
TESTS_DIR = PROJECT_ROOT / "tests"

def _setup_sys_path():
    """Ensure project-specific paths are available before project imports."""
    for p in (COMMON_PY_DIR, LIBS_DIR, INFRA_DIR, PROJECT_ROOT, TESTS_DIR):
        ps = str(p)
        if ps in sys.path:
            continue
        sys.path.insert(0, ps)

_setup_sys_path()

import pytest
import pytest_asyncio
from typing import Dict, Any

from support.feature_extraction_spy import FeatureExtractionSpy
from support.db_cleanup import FeatureExtractionCleanup, FeatureExtractionStateValidator
from support.observability_validator import ObservabilityValidator
from support.event_publisher import FeatureExtractionEventPublisher
from config import config


@pytest.mark.integration
@pytest.mark.feature_extraction
class TestFeatureExtractionPhase:
    """Feature Extraction Phase Integration Tests"""

    @pytest_asyncio.fixture
    async def feature_extraction_spy(self, message_broker):
        """Feature extraction message spy fixture"""
        spy = FeatureExtractionSpy(config.BUS_BROKER)
        await spy.connect()
        yield spy
        await spy.disconnect()

    @pytest_asyncio.fixture
    async def feature_extraction_cleanup(self, db_manager):
        """Feature extraction database cleanup fixture"""
        cleanup = FeatureExtractionCleanup(db_manager)
        await cleanup.cleanup_test_data()
        yield cleanup
        await cleanup.cleanup_test_data()

    @pytest_asyncio.fixture
    async def feature_extraction_state_validator(self, db_manager):
        """Feature extraction state validator fixture"""
        return FeatureExtractionStateValidator(db_manager)

    @pytest_asyncio.fixture
    async def feature_extraction_event_publisher(self, message_broker):
        """Feature extraction event publisher fixture"""
        publisher = FeatureExtractionEventPublisher(message_broker)
        yield publisher
        publisher.clear_published_events()

    @pytest_asyncio.fixture
    async def feature_extraction_test_environment(
        self,
        db_manager,
        message_broker,
        feature_extraction_spy,
        feature_extraction_cleanup,
        observability_validator,
        feature_extraction_event_publisher,
        feature_extraction_state_validator
    ):
        """Complete feature extraction test environment"""
        # Clear any existing messages and ensure clean DB state
        feature_extraction_spy.clear_messages()
        await feature_extraction_cleanup.cleanup_test_data()

        # Start observability capture
        observability_validator.start_observability_capture()

        yield {
            "spy": feature_extraction_spy,
            "cleanup": feature_extraction_cleanup,
            "validator": feature_extraction_state_validator,
            "publisher": feature_extraction_event_publisher,
            "observability": observability_validator,
            "db_manager": db_manager,
            "message_broker": message_broker
        }

        # Stop capture and clean up
        try:
            observability_validator.stop_observability_capture()
            observability_validator.clear_all_captures()
        finally:
            await feature_extraction_cleanup.cleanup_test_data()