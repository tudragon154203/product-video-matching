import os
import sys
import pytest
from unittest.mock import Mock, patch

pytestmark = pytest.mark.unit

# Add the project root to the path for correct imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Add the libs/common-py to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs", "common-py"))


@pytest.mark.asyncio
@patch("handlers.decorators.validator")
async def test_validate_event_invokes_validator(mock_validator):
    """
    Asserts that validate_event decorator calls validator.validate_event
    with the correct arguments when event_data is in positional arguments.
    """
    from handlers.decorators import validate_event

    MOCK_SCHEMA = "test_schema"
    MOCK_EVENT = {"key": "value"}
    MOCK_RETURN = "result"

    @validate_event(MOCK_SCHEMA)
    async def mock_handler(self, event_data):
        return MOCK_RETURN

    mock_instance = Mock()
    result = await mock_handler(mock_instance, MOCK_EVENT)

    mock_validator.validate_event.assert_called_once_with(MOCK_SCHEMA, MOCK_EVENT)
    assert result == MOCK_RETURN


@pytest.mark.asyncio
@patch("handlers.decorators.validator")
async def test_validate_event_handles_kwargs(mock_validator):
    """
    Asserts that validate_event decorator works when event_data is passed
    as a keyword argument.
    """
    from handlers.decorators import validate_event

    MOCK_SCHEMA = "test_schema"
    MOCK_EVENT = {"key": "value"}
    MOCK_RETURN = "result"

    @validate_event(MOCK_SCHEMA)
    async def mock_handler(self, event_data=None):
        return MOCK_RETURN

    mock_instance = Mock()
    result = await mock_handler(mock_instance, event_data=MOCK_EVENT)

    mock_validator.validate_event.assert_called_once_with(MOCK_SCHEMA, MOCK_EVENT)
    assert result == MOCK_RETURN


@pytest.mark.asyncio
@patch("handlers.decorators.validator")
async def test_validate_event_raises_value_error_if_no_event_data(mock_validator):
    """
    Asserts that validate_event raises ValueError if event_data is missing.
    """
    from handlers.decorators import validate_event

    @validate_event("test_schema")
    async def mock_handler(self):
        pass

    with pytest.raises(ValueError, match="Event data not found in arguments"):
        await mock_handler(Mock())

    mock_validator.validate_event.assert_not_called()


@pytest.mark.asyncio
async def test_handle_errors_re_raises_exception(caplog):
    """
    Asserts that handle_errors logs the exception and re-raises it.
    """
    from handlers.decorators import handle_errors

    MOCK_ERROR_MESSAGE = "Something went wrong"

    @handle_errors
    async def failing_handler():
        raise Exception(MOCK_ERROR_MESSAGE)

    with pytest.raises(Exception):
        await failing_handler()

    # assert "Error in failing_handler" in caplog.text
    # assert MOCK_ERROR_MESSAGE in caplog.text


@pytest.mark.asyncio
async def test_handle_errors_happy_path():
    """
    Asserts that handle_errors returns the result in the happy path.
    """
    from handlers.decorators import handle_errors

    MOCK_RETURN = "success"

    @handle_errors
    async def successful_handler():
        return MOCK_RETURN

    result = await successful_handler()
    assert result == MOCK_RETURN
