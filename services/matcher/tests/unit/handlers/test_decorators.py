"""Unit tests for decorators module."""

from unittest.mock import MagicMock, patch

import pytest

from handlers.decorators import handle_errors, validate_event


class TestValidateEvent:
    """Test the validate_event decorator."""

    @pytest.mark.asyncio
    async def test_validate_event_success(self):
        """Test successful validation with valid event data."""
        # Mock the validator
        mock_validator = MagicMock()
        mock_validator.validate_event = MagicMock()

        with patch('handlers.decorators.validator', mock_validator):
            @validate_event("test_schema")
            async def test_function(self, event_data):
                return {"result": "success"}

            result = await test_function(None, {"test": "data"})

            # Verify validator was called
            mock_validator.validate_event.assert_called_once_with("test_schema", {"test": "data"})
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_validate_event_with_kwargs(self):
        """Test validation when event_data is passed as kwargs."""
        mock_validator = MagicMock()
        mock_validator.validate_event = MagicMock()

        with patch('handlers.decorators.validator', mock_validator):
            @validate_event("test_schema")
            async def test_function(self, event_data):
                return {"result": "success"}

            result = await test_function(self=None, event_data={"test": "data"})

            mock_validator.validate_event.assert_called_once_with("test_schema", {"test": "data"})
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_validate_event_missing_event_data(self):
        """Test validation failure when event_data is missing."""
        mock_validator = MagicMock()
        mock_validator.validate_event = MagicMock()

        with patch('handlers.decorators.validator', mock_validator):
            @validate_event("test_schema")
            async def test_function(self):
                return {"result": "success"}

            with pytest.raises(ValueError, match="Event data not found in arguments"):
                await test_function(None)

            # Validator should not be called
            mock_validator.validate_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_event_none_event_data(self):
        """Test validation failure when event_data is None."""
        mock_validator = MagicMock()
        mock_validator.validate_event = MagicMock()

        with patch('handlers.decorators.validator', mock_validator):
            @validate_event("test_schema")
            async def test_function(self, event_data):
                return {"result": "success"}

            with pytest.raises(ValueError, match="Event data not found in arguments"):
                await test_function(None, None)

            mock_validator.validate_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_event_propagates_validation_error(self):
        """Test that validation errors are properly propagated."""
        mock_validator = MagicMock()
        mock_validator.validate_event.side_effect = ValueError("Invalid schema")

        with patch('handlers.decorators.validator', mock_validator):
            @validate_event("test_schema")
            async def test_function(self, event_data):
                return {"result": "success"}

            with pytest.raises(ValueError, match="Invalid schema"):
                await test_function(None, {"invalid": "data"})

            mock_validator.validate_event.assert_called_once_with("test_schema", {"invalid": "data"})


class TestHandleErrors:
    """Test the handle_errors decorator."""

    @pytest.mark.asyncio
    async def test_handle_errors_success(self):
        """Test successful function execution without errors."""
        mock_logger = MagicMock()

        with patch('handlers.decorators.logger', mock_logger):
            @handle_errors
            async def test_function():
                return {"result": "success"}

            result = await test_function()

            assert result == {"result": "success"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_errors_logs_and_reraises(self):
        """Test that errors are logged and then re-raised."""
        mock_logger = MagicMock()

        with patch('handlers.decorators.logger', mock_logger):
            @handle_errors
            async def test_function():
                raise ValueError("Test error")

            with pytest.raises(ValueError, match="Test error"):
                await test_function()

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert "Error in test_function" in error_call[0][0]
            assert "Test error" in error_call[1]["error"]

    @pytest.mark.asyncio
    async def test_handle_errors_with_different_exception_types(self):
        """Test error handling with different exception types."""
        mock_logger = MagicMock()

        with patch('handlers.decorators.logger', mock_logger):
            @handle_errors
            async def test_function():
                raise RuntimeError("Runtime error")

            with pytest.raises(RuntimeError, match="Runtime error"):
                await test_function()

            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert "Error in test_function" in error_call[0][0]
            assert "Runtime error" in error_call[1]["error"]

    @pytest.mark.asyncio
    async def test_handle_errors_preserves_function_metadata(self):
        """Test that function metadata is preserved by decorator."""
        mock_logger = MagicMock()

        with patch('handlers.decorators.logger', mock_logger):
            @handle_errors
            async def test_function():
                """Test function docstring."""
                return {"result": "success"}

            # Verify metadata is preserved
            assert test_function.__name__ == "test_function"
            assert test_function.__doc__ == "Test function docstring."

            result = await test_function()
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_combined_decorators(self):
        """Test validate_event and handle_errors decorators working together."""
        mock_validator = MagicMock()
        mock_validator.validate_event = MagicMock()
        mock_logger = MagicMock()

        with patch('handlers.decorators.validator', mock_validator), \
                patch('handlers.decorators.logger', mock_logger):

            @validate_event("test_schema")
            @handle_errors
            async def test_function(self, event_data):
                if event_data.get("should_fail"):
                    raise ValueError("Function error")
                return {"result": "success"}

            # Test success case
            result = await test_function(None, {"test": "data"})
            assert result == {"result": "success"}
            mock_validator.validate_event.assert_called_once()

            # Reset mocks
            mock_validator.reset_mock()
            mock_logger.reset_mock()

            # Test validation error
            with pytest.raises(ValueError, match="Invalid schema"):
                mock_validator.validate_event.side_effect = ValueError("Invalid schema")
                await test_function(None, {"test": "data"})

            # Reset mocks
            mock_validator.reset_mock()
            mock_logger.reset_mock()
            mock_validator.validate_event.side_effect = None

            # Test function error
            with pytest.raises(ValueError, match="Function error"):
                await test_function(None, {"should_fail": True})

            # Both validation should happen and error should be logged
            mock_validator.validate_event.assert_called_once()
            mock_logger.error.assert_called_once()
