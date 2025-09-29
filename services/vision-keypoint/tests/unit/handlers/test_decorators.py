from unittest.mock import Mock, patch
import pytest
from handlers.decorators import validate_event


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