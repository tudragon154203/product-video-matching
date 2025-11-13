import pytest
from unittest.mock import Mock, patch

from handlers.decorators import validate_event, handle_errors
from contracts.validator import validator


class TestValidateEventDecorator:
    """Test cases for the validate_event decorator fix"""

    @pytest.mark.asyncio
    async def test_validate_event_with_instance_method(self):
        """Test that the decorator correctly extracts event_data from instance methods"""
        # Mock validator to avoid actual schema validation
        with patch.object(validator, 'validate_event') as mock_validate:
            mock_validate.return_value = None

            @validate_event("test_schema")
            async def test_handler(self, event_data):
                return event_data

            # Create a mock instance
            mock_instance = Mock()

            # Call the decorated method as an instance method
            test_event = {"test": "data"}
            result = await test_handler(mock_instance, test_event)

            # Verify validator was called with correct schema and event data
            mock_validate.assert_called_once_with("test_schema", test_event)
            assert result == test_event

    @pytest.mark.asyncio
    async def test_validate_event_with_regular_function(self):
        """Test that the decorator works with regular functions too"""
        with patch.object(validator, 'validate_event') as mock_validate:
            mock_validate.return_value = None

            @validate_event("test_schema")
            async def test_function(event_data):
                return event_data

            # Call the decorated function directly
            test_event = {"test": "data"}
            result = await test_function(test_event)

            # Verify validator was called with correct schema and event data
            mock_validate.assert_called_once_with("test_schema", test_event)
            assert result == test_event

    @pytest.mark.asyncio
    async def test_validate_event_with_kwargs(self):
        """Test that the decorator works when event_data is passed as kwarg"""
        with patch.object(validator, 'validate_event') as mock_validate:
            mock_validate.return_value = None

            @validate_event("test_schema")
            async def test_handler(self, event_data):
                return event_data

            mock_instance = Mock()
            test_event = {"test": "data"}

            # Call with event_data as kwarg
            result = await test_handler(mock_instance, event_data=test_event)

            mock_validate.assert_called_once_with("test_schema", test_event)
            assert result == test_event

    @pytest.mark.asyncio
    async def test_validate_event_missing_data_raises_error(self):
        """Test that the decorator raises ValueError when event_data is missing"""
        with patch.object(validator, 'validate_event'):
            @validate_event("products_image_masked")  # Use a real schema
            async def test_handler(self):
                return "should not reach here"

            mock_instance = Mock()

            with pytest.raises(ValueError, match="Event data not found in arguments"):
                await test_handler(mock_instance)

    @pytest.mark.asyncio
    async def test_validate_event_propagates_validation_errors(self):
        """Test that validation errors are properly propagated"""
        with patch.object(validator, 'validate_event') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")

            @validate_event("test_schema")
            async def test_handler(self, event_data):
                return event_data

            mock_instance = Mock()
            test_event = {"test": "data"}

            with pytest.raises(Exception, match="Validation failed"):
                await test_handler(mock_instance, test_event)

            # Verify validator was still called
            mock_validate.assert_called_once_with("test_schema", test_event)

    @pytest.mark.asyncio
    async def test_validate_event_with_correlation_id_param(self):
        """Test decorator works with handler methods that have correlation_id parameter"""
        with patch.object(validator, 'validate_event') as mock_validate:
            mock_validate.return_value = None

            @validate_event("test_schema")
            async def test_handler_with_correlation(self, event_data, correlation_id: str = None):
                return {"event": event_data, "correlation_id": correlation_id}

            mock_instance = Mock()
            test_event = {"test": "data"}
            correlation_id = "test-correlation-123"

            result = await test_handler_with_correlation(mock_instance, test_event, correlation_id)

            mock_validate.assert_called_once_with("test_schema", test_event)
            assert result["event"] == test_event
            assert result["correlation_id"] == correlation_id


class TestHandleErrorsDecorator:
    """Test cases for the handle_errors decorator"""

    @pytest.mark.asyncio
    async def test_handle_errors_success(self):
        """Test that handle_errors decorator allows successful execution"""
        @handle_errors
        async def successful_handler(data):
            return {"status": "success", "data": data}

        result = await successful_handler("test_data")
        assert result == {"status": "success", "data": "test_data"}

    @pytest.mark.asyncio
    async def test_handle_errors_propagates_exceptions(self):
        """Test that handle_errors decorator propagates exceptions after logging"""
        @handle_errors
        async def failing_handler(data):
            raise ValueError("Test error")

        with patch("handlers.decorators.logger") as mock_logger:
            with pytest.raises(ValueError, match="Test error"):
                await failing_handler("test_data")

            # Verify error was logged
            mock_logger.error.assert_called_once_with(
                "Handler raised an exception",
                handler="failing_handler",
                error="Test error",
            )

    @pytest.mark.asyncio
    async def test_combined_decorators(self):
        """Test validate_event and handle_errors decorators work together"""
        with patch.object(validator, 'validate_event') as mock_validate:
            mock_validate.return_value = None

            @validate_event("test_schema")
            @handle_errors
            async def combined_handler(self, event_data):
                return {"processed": event_data}

            mock_instance = Mock()
            test_event = {"test": "data"}

            result = await combined_handler(mock_instance, test_event)

            # Validation should have passed
            mock_validate.assert_called_once_with("test_schema", test_event)
            assert result == {"processed": test_event}
