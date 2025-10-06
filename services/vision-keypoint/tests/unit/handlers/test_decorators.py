from unittest.mock import Mock, patch
import pytest
from handlers.decorators import validate_event, handle_errors


class TestDecorators:
    """Unit tests for decorators module"""

    @pytest.mark.unit
    @patch('handlers.decorators.validator')
    async def test_validate_event_decorator_success(self, mock_validator):
        """Test the validate_event decorator with valid data"""
        # Setup
        mock_validator.validate_event = Mock()

        # Define a test async function - this follows the pattern of handler functions that receive event_data
        @validate_event("test_schema")
        async def test_func(self_param, event_data):
            return "success"

        # Call the decorated function with valid event data (like handler methods are called)
        result = await test_func(self, {"valid": "data"})

        # Verify that validation was called
        mock_validator.validate_event.assert_called_once_with("test_schema", {"valid": "data"})

        # Verify the function returned the expected result
        assert result == "success"

    @pytest.mark.unit
    @patch('handlers.decorators.validator')
    async def test_validate_event_decorator_failure(self, mock_validator):
        """Test the validate_event decorator with invalid data"""
        # Setup to raise an exception on validation
        mock_validator.validate_event.side_effect = ValueError("Validation failed")

        # Define a test async function - this follows the pattern of handler functions that receive event_data
        @validate_event("test_schema")
        async def test_func(self_param, event_data):
            return "success"

        # Call the decorated function and expect an exception
        with pytest.raises(ValueError, match="Validation failed"):
            await test_func(self, {"invalid": "data"})

        # Verify that validation was called
        mock_validator.validate_event.assert_called_once_with("test_schema", {"invalid": "data"})

    @pytest.mark.unit
    @patch('handlers.decorators.validator')
    @patch('handlers.decorators.logger')
    async def test_validate_event_decorator_no_event_data(self, mock_logger, mock_validator):
        """Test the validate_event decorator when no event_data is present"""
        # Define a test async function that expects event_data
        @validate_event("test_schema")
        async def test_func(self_param, event_data):
            return "success"

        # Call the decorated function without event_data
        with pytest.raises(ValueError, match="Event data not found in arguments"):
            await test_func(self)  # No event_data provided

        # Verify that validator was not called since no event_data was found
        mock_validator.validate_event.assert_not_called()

    @pytest.mark.unit
    @patch('handlers.decorators.validator')
    @patch('handlers.decorators.logger')
    async def test_validate_event_decorator_no_event_data_kwargs(self, mock_logger, mock_validator):
        """Test the validate_event decorator when event_data not in kwargs"""
        # Define a test async function that expects event_data via kwargs
        @validate_event("test_schema")
        async def test_func(self_param, **kwargs):
            return "success"

        # Call the decorated function without event_data in kwargs
        with pytest.raises(ValueError, match="Event data not found in arguments"):
            await test_func(self, other_param="value")  # No event_data in kwargs

        # Verify that validator was not called since no event_data was found
        mock_validator.validate_event.assert_not_called()

    @pytest.mark.unit
    @patch('handlers.decorators.validator')
    @patch('handlers.decorators.logger')
    async def test_validate_event_decorator_validator_raises(self, mock_logger, mock_validator):
        """Test the validate_event decorator when validator.validate_event raises"""
        # Setup validator to raise a different exception
        mock_validator.validate_event.side_effect = RuntimeError("Schema validation error")

        # Define a test async function
        @validate_event("test_schema")
        async def test_func(self_param, event_data):
            return "success"

        # Call the decorated function and expect the exception to be re-raised
        with pytest.raises(RuntimeError, match="Schema validation error"):
            await test_func(self, {"valid": "data"})

        # Verify that validation was called and error was logged
        mock_validator.validate_event.assert_called_once_with("test_schema", {"valid": "data"})
        mock_logger.error.assert_called_once_with("Validation failed for test_schema: Schema validation error")

    @pytest.mark.unit
    @patch('handlers.decorators.validator')
    @patch('handlers.decorators.logger')
    async def test_validate_event_decorator_with_kwargs(self, mock_logger, mock_validator):
        """Test the validate_event decorator when event_data is in kwargs"""
        # Setup
        mock_validator.validate_event = Mock()

        # Define a test async function that takes event_data via kwargs
        @validate_event("test_schema")
        async def test_func(self_param, **kwargs):
            return "success"

        # Call the decorated function with event_data in kwargs
        result = await test_func(self, event_data={"valid": "data"})

        # Verify that validation was called and function succeeded
        mock_validator.validate_event.assert_called_once_with("test_schema", {"valid": "data"})
        assert result == "success"

    @pytest.mark.unit
    @patch('handlers.decorators.logger')
    async def test_handle_errors_decorator_success(self, mock_logger):
        """Test the handle_errors decorator with successful execution"""
        # Define a test async function that succeeds
        @handle_errors
        async def test_func(self_param):
            return "success"

        # Call the decorated function
        result = await test_func(self)

        # Verify the function returned the expected result and no error was logged
        assert result == "success"
        mock_logger.error.assert_not_called()

    @pytest.mark.unit
    @patch('handlers.decorators.logger')
    async def test_handle_errors_decorator_with_exception(self, mock_logger):
        """Test the handle_errors decorator when exception occurs"""
        # Define a test async function that raises an exception
        @handle_errors
        async def test_func(self_param):
            raise ValueError("Something went wrong")

        # Call the decorated function and expect exception to be re-raised
        with pytest.raises(ValueError, match="Something went wrong"):
            await test_func(self)

        # Verify that error was logged
        mock_logger.error.assert_called_once_with("Error in test_func: Something went wrong")
