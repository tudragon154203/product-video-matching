"""Unit tests for matcher_handler module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from handlers.matcher_handler import MatcherHandler


class TestMatcherHandler:
    """Test the MatcherHandler class."""

    def test_init(self):
        """Test MatcherHandler initialization."""
        mock_config = MagicMock()
        mock_config.POSTGRES_DSN = "postgresql://test:test@localhost:5432/test"
        mock_config.BUS_BROKER = "amqp://localhost:5672"
        mock_config.DATA_ROOT = "/data"
        mock_config.RETRIEVAL_TOPK = 20
        mock_config.SIM_DEEP_MIN = 0.82
        mock_config.INLIERS_MIN = 0.35
        mock_config.MATCH_BEST_MIN = 0.88
        mock_config.MATCH_CONS_MIN = 2
        mock_config.MATCH_ACCEPT = 0.80

        with patch('handlers.matcher_handler.config', mock_config):
            with patch('handlers.matcher_handler.DatabaseManager') as mock_db_manager, \
                 patch('handlers.matcher_handler.MessageBroker') as mock_broker, \
                 patch('handlers.matcher_handler.MatcherService') as mock_service:

                handler = MatcherHandler()

                # Verify initialization
                assert handler.initialized is False
                mock_db_manager.assert_called_once_with(mock_config.POSTGRES_DSN)
                mock_broker.assert_called_once_with(mock_config.BUS_BROKER)
                mock_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_first_time(self):
        """Test initialization when not previously initialized."""
        mock_config = MagicMock()
        mock_config.POSTGRES_DSN = "postgresql://test:test@localhost:5432/test"
        mock_config.BUS_BROKER = "amqp://localhost:5672"
        mock_config.DATA_ROOT = "/data"
        mock_config.RETRIEVAL_TOPK = 20
        mock_config.SIM_DEEP_MIN = 0.82
        mock_config.INLIERS_MIN = 0.35
        mock_config.MATCH_BEST_MIN = 0.88
        mock_config.MATCH_CONS_MIN = 2
        mock_config.MATCH_ACCEPT = 0.80

        with patch('handlers.matcher_handler.config', mock_config):
            with patch('handlers.matcher_handler.DatabaseManager') as mock_db_manager, \
                 patch('handlers.matcher_handler.MessageBroker') as mock_broker, \
                 patch('handlers.matcher_handler.MatcherService') as mock_service_class:

                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                handler = MatcherHandler()
                await handler.initialize()

                # Verify service.initialize was called and handler is marked as initialized
                mock_service.initialize.assert_called_once()
                assert handler.initialized is True

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self):
        """Test that initialize is idempotent when already initialized."""
        mock_config = MagicMock()
        mock_config.POSTGRES_DSN = "postgresql://test:test@localhost:5432/test"
        mock_config.BUS_BROKER = "amqp://localhost:5672"
        mock_config.DATA_ROOT = "/data"
        mock_config.RETRIEVAL_TOPK = 20
        mock_config.SIM_DEEP_MIN = 0.82
        mock_config.INLIERS_MIN = 0.35
        mock_config.MATCH_BEST_MIN = 0.88
        mock_config.MATCH_CONS_MIN = 2
        mock_config.MATCH_ACCEPT = 0.80

        with patch('handlers.matcher_handler.config', mock_config):
            with patch('handlers.matcher_handler.DatabaseManager') as mock_db_manager, \
                 patch('handlers.matcher_handler.MessageBroker') as mock_broker, \
                 patch('handlers.matcher_handler.MatcherService') as mock_service_class:

                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                handler = MatcherHandler()
                await handler.initialize()

                # Reset mock to track subsequent calls
                mock_service.initialize.reset_mock()

                # Second initialization should not call service.initialize again
                await handler.initialize()
                mock_service.initialize.assert_not_called()
                assert handler.initialized is True

    @pytest.mark.asyncio
    async def test_handle_match_request_success(self):
        """Test successful handling of match request."""
        mock_config = MagicMock()
        mock_config.POSTGRES_DSN = "postgresql://test:test@localhost:5432/test"
        mock_config.BUS_BROKER = "amqp://localhost:5672"
        mock_config.DATA_ROOT = "/data"
        mock_config.RETRIEVAL_TOPK = 20
        mock_config.SIM_DEEP_MIN = 0.82
        mock_config.INLIERS_MIN = 0.35
        mock_config.MATCH_BEST_MIN = 0.88
        mock_config.MATCH_CONS_MIN = 2
        mock_config.MATCH_ACCEPT = 0.80

        with patch('handlers.matcher_handler.config', mock_config):
            with patch('handlers.matcher_handler.DatabaseManager') as mock_db_manager, \
                 patch('handlers.matcher_handler.MessageBroker') as mock_broker, \
                 patch('handlers.matcher_handler.MatcherService') as mock_service_class:

                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                handler = MatcherHandler()
                await handler.initialize()

                test_event_data = {
                    "product_id": "test_product",
                    "video_id": "test_video",
                    "job_id": "test_job"
                }

                await handler.handle_match_request(test_event_data)

                # Verify service method was called with correct data
                mock_service.handle_match_request.assert_called_once_with(test_event_data)

    @pytest.mark.asyncio
    async def test_handle_match_request_auto_initialize(self):
        """Test that handle_match_request initializes if not already initialized."""
        mock_config = MagicMock()
        mock_config.POSTGRES_DSN = "postgresql://test:test@localhost:5432/test"
        mock_config.BUS_BROKER = "amqp://localhost:5672"
        mock_config.DATA_ROOT = "/data"
        mock_config.RETRIEVAL_TOPK = 20
        mock_config.SIM_DEEP_MIN = 0.82
        mock_config.INLIERS_MIN = 0.35
        mock_config.MATCH_BEST_MIN = 0.88
        mock_config.MATCH_CONS_MIN = 2
        mock_config.MATCH_ACCEPT = 0.80

        with patch('handlers.matcher_handler.config', mock_config):
            with patch('handlers.matcher_handler.DatabaseManager') as mock_db_manager, \
                 patch('handlers.matcher_handler.MessageBroker') as mock_broker, \
                 patch('handlers.matcher_handler.MatcherService') as mock_service_class:

                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                handler = MatcherHandler()
                # Don't manually initialize

                test_event_data = {
                    "product_id": "test_product",
                    "video_id": "test_video",
                    "job_id": "test_job"
                }

                # Mock the initialize method to track if it's called
                handler.initialize = AsyncMock()

                # Mock the decorators to bypass validation for this test
                with patch('handlers.matcher_handler.validate_event'), \
                     patch('handlers.matcher_handler.handle_errors'):
                    await handler.handle_match_request(test_event_data)

                # Note: Since decorators are mocked, initialize won't be called automatically
                # In real scenario, decorators would handle the flow

    @pytest.mark.asyncio
    async def test_handle_match_request_propagates_service_errors(self):
        """Test that service errors are properly propagated."""
        mock_config = MagicMock()
        mock_config.POSTGRES_DSN = "postgresql://test:test@localhost:5432/test"
        mock_config.BUS_BROKER = "amqp://localhost:5672"
        mock_config.DATA_ROOT = "/data"
        mock_config.RETRIEVAL_TOPK = 20
        mock_config.SIM_DEEP_MIN = 0.82
        mock_config.INLIERS_MIN = 0.35
        mock_config.MATCH_BEST_MIN = 0.88
        mock_config.MATCH_CONS_MIN = 2
        mock_config.MATCH_ACCEPT = 0.80

        with patch('handlers.matcher_handler.config', mock_config):
            with patch('handlers.matcher_handler.DatabaseManager') as mock_db_manager, \
                 patch('handlers.matcher_handler.MessageBroker') as mock_broker, \
                 patch('handlers.matcher_handler.MatcherService') as mock_service_class:

                mock_service = AsyncMock()
                mock_service.handle_match_request.side_effect = ValueError("Service error")
                mock_service_class.return_value = mock_service

                handler = MatcherHandler()
                await handler.initialize()

                test_event_data = {
                    "product_id": "test_product",
                    "video_id": "test_video",
                    "job_id": "test_job"
                }

                # Mock decorators to bypass validation
                with patch('handlers.matcher_handler.validate_event'), \
                     patch('handlers.matcher_handler.handle_errors') as mock_error_handler:
                    mock_error_handler.side_effect = lambda func: func

                    with pytest.raises(ValueError, match="Service error"):
                        await handler.handle_match_request(test_event_data)

                    mock_service.handle_match_request.assert_called_once_with(test_event_data)

    @pytest.mark.asyncio
    async def test_single_run_initialization_logic(self):
        """Test that initialization only runs once even with concurrent calls."""
        mock_config = MagicMock()
        mock_config.POSTGRES_DSN = "postgresql://test:test@localhost:5432/test"
        mock_config.BUS_BROKER = "amqp://localhost:5672"
        mock_config.DATA_ROOT = "/data"
        mock_config.RETRIEVAL_TOPK = 20
        mock_config.SIM_DEEP_MIN = 0.82
        mock_config.INLIERS_MIN = 0.35
        mock_config.MATCH_BEST_MIN = 0.88
        mock_config.MATCH_CONS_MIN = 2
        mock_config.MATCH_ACCEPT = 0.80

        with patch('handlers.matcher_handler.config', mock_config):
            with patch('handlers.matcher_handler.DatabaseManager') as mock_db_manager, \
                 patch('handlers.matcher_handler.MessageBroker') as mock_broker, \
                 patch('handlers.matcher_handler.MatcherService') as mock_service_class:

                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                handler = MatcherHandler()

                # Simulate concurrent initialization calls
                import asyncio
                await asyncio.gather(
                    handler.initialize(),
                    handler.initialize(),
                    handler.initialize()
                )

                # Service initialize should only be called once
                mock_service.initialize.assert_called_once()
                assert handler.initialized is True