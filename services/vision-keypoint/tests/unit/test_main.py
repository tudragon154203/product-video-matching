from unittest.mock import AsyncMock, patch
import pytest

from main import service_context


class TestMain:
    """Unit tests for main module"""

    @pytest.mark.unit
    @patch('main.VisionKeypointHandler')
    async def test_service_context_full_lifecycle(self, mock_handler_class):
        """Test service_context lifecycle: initialize, yield, and teardown"""
        # Setup mock handler
        mock_handler = AsyncMock()
        mock_handler_class.return_value = mock_handler

        # Test the context manager
        async with service_context() as handler:
            # Verify handler is the mocked instance
            assert handler == mock_handler

            # Verify initialization calls were made
            mock_handler.db.connect.assert_called_once()
            mock_handler.broker.connect.assert_called_once()
            mock_handler.initialize.assert_called_once()

        # Verify cleanup calls were made after context exit
        mock_handler.broker.disconnect.assert_called_once()
        mock_handler.db.disconnect.assert_called_once()

    @pytest.mark.unit
    @patch('main.VisionKeypointHandler')
    async def test_service_context_exception_handling(self, mock_handler_class):
        """Test service_context properly handles exceptions during initialization"""
        # Setup mock handler to raise during db.connect
        mock_handler = AsyncMock()
        mock_handler.db.connect.side_effect = Exception("Database connection failed")
        mock_handler_class.return_value = mock_handler

        # Test that exception propagates
        with pytest.raises(Exception, match="Database connection failed"):
            async with service_context():
                pass

        # Verify that teardown is still called even when initialization fails
        # Note: Since db.connect fails, broker.connect and initialize won't be called
        mock_handler.db.connect.assert_called_once()
        # But disconnect should still be called in finally block
        mock_handler.broker.disconnect.assert_called_once()

    @pytest.mark.unit
    @patch('main.VisionKeypointHandler')
    async def test_service_context_exception_in_user_code(self, mock_handler_class):
        """Test service_context handles exceptions in user code properly"""
        # Setup mock handler
        mock_handler = AsyncMock()
        mock_handler_class.return_value = mock_handler

        # Test that exception in user code doesn't prevent cleanup
        with pytest.raises(ValueError, match="User error"):
            async with service_context() as _:
                raise ValueError("User error")

        # Verify all calls were made properly
        mock_handler.db.connect.assert_called_once()
        mock_handler.broker.connect.assert_called_once()
        mock_handler.initialize.assert_called_once()
        mock_handler.broker.disconnect.assert_called_once()
        mock_handler.db.disconnect.assert_called_once()

    @pytest.mark.unit
    @patch('main.VisionKeypointHandler')
    async def test_service_context_break_out_early(self, mock_handler_class):
        """Test service_context handles breaking out early (e.g., via break or return)"""
        # Setup mock handler
        mock_handler = AsyncMock()
        mock_handler_class.return_value = mock_handler

        result = None
        async with service_context() as _:
            result = "early_exit"
            # Simulate early exit - context manager will exit normally

        # Verify result was set and cleanup still happened
        assert result == "early_exit"
        mock_handler.db.connect.assert_called_once()
        mock_handler.broker.connect.assert_called_once()
        mock_handler.initialize.assert_called_once()
        mock_handler.broker.disconnect.assert_called_once()
        mock_handler.db.disconnect.assert_called_once()
