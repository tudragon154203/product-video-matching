"""Unit tests for main.py prefetch_count configuration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_subscribe_with_prefetch_count_one():
    """Test that video search request subscription uses prefetch_count=1."""
    mock_handler = MagicMock()
    mock_handler.db = MagicMock()
    mock_handler.db.connect = AsyncMock()
    mock_handler.db.disconnect = AsyncMock()
    mock_handler.broker = MagicMock()
    mock_handler.broker.connect = AsyncMock()
    mock_handler.broker.disconnect = AsyncMock()
    mock_handler.broker.subscribe_to_topic = AsyncMock()
    mock_handler.handle_videos_search_request = AsyncMock()
    
    with patch('main.VideoCrawlHandler', return_value=mock_handler), \
         patch('main.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # Make sleep raise to exit the infinite loop
        mock_sleep.side_effect = KeyboardInterrupt()
        
        from main import main
        
        try:
            await main()
        except KeyboardInterrupt:
            pass
        
        # Verify subscribe_to_topic was called with prefetch_count=1
        mock_handler.broker.subscribe_to_topic.assert_called_once_with(
            "videos.search.request",
            mock_handler.handle_videos_search_request,
            prefetch_count=1
        )


@pytest.mark.asyncio
async def test_service_context_initializes_connections():
    """Test that service context properly initializes database and broker connections."""
    mock_handler = MagicMock()
    mock_handler.db = MagicMock()
    mock_handler.db.connect = AsyncMock()
    mock_handler.db.disconnect = AsyncMock()
    mock_handler.broker = MagicMock()
    mock_handler.broker.connect = AsyncMock()
    mock_handler.broker.disconnect = AsyncMock()
    
    with patch('main.VideoCrawlHandler', return_value=mock_handler):
        from main import service_context
        
        async with service_context() as handler:
            # Verify connections were established
            handler.db.connect.assert_called_once()
            handler.broker.connect.assert_called_once()
        
        # Verify cleanup was performed
        handler.db.disconnect.assert_called_once()
        handler.broker.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_service_context_cleanup_on_exception():
    """Test that service context cleans up resources even on exception."""
    mock_handler = MagicMock()
    mock_handler.db = MagicMock()
    mock_handler.db.connect = AsyncMock()
    mock_handler.db.disconnect = AsyncMock()
    mock_handler.broker = MagicMock()
    mock_handler.broker.connect = AsyncMock()
    mock_handler.broker.disconnect = AsyncMock()
    
    with patch('main.VideoCrawlHandler', return_value=mock_handler):
        from main import service_context
        
        try:
            async with service_context() as handler:
                # Trigger an exception
                raise Exception("Test error")
        except Exception:
            pass
        
        # Verify cleanup was still performed
        handler.db.disconnect.assert_called_once()
        handler.broker.disconnect.assert_called_once()
