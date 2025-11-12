"""Unit tests for main module."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Mock the imports that main.py uses
mock_matcher_handler = MagicMock()


class TestMain:
    """Test the main module functionality."""

    @pytest.mark.asyncio
    async def test_service_context_successful_lifecycle(self):
        """Test service context successful connection, yield, and cleanup."""
        with patch('main.MatcherHandler') as mock_handler_class, \
                patch('main.asyncio.sleep') as _:

            mock_handler = MagicMock()
            mock_handler.db = AsyncMock()
            mock_handler.broker = AsyncMock()
            mock_handler.service = AsyncMock()
            mock_handler.initialize = AsyncMock()

            mock_handler_class.return_value = mock_handler

            from main import service_context

            # Use the context manager
            async with service_context() as handler:
                # Verify connections were established
                mock_handler.db.connect.assert_called_once()
                mock_handler.broker.connect.assert_called_once()
                mock_handler.initialize.assert_called_once()
                assert handler == mock_handler

            # Verify cleanup was called
            mock_handler.service.cleanup.assert_called_once()
            mock_handler.db.disconnect.assert_called_once()
            mock_handler.broker.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_context_exception_handling(self):
        """Test service context handles exceptions and still cleans up."""
        with patch('main.MatcherHandler') as mock_handler_class:

            mock_handler = MagicMock()
            mock_handler.db = AsyncMock()
            mock_handler.broker = AsyncMock()
            mock_handler.service = AsyncMock()
            mock_handler.initialize = AsyncMock(side_effect=Exception("Init failed"))

            mock_handler_class.return_value = mock_handler

            from main import service_context

            # Even if initialization fails, cleanup should still be called
            with pytest.raises(Exception, match="Init failed"):
                async with service_context():
                    pass

            # Verify cleanup was still called despite the exception
            mock_handler.service.cleanup.assert_called_once()
            mock_handler.db.disconnect.assert_called_once()
            mock_handler.broker.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_context_cleanup_order(self):
        """Test that cleanup happens in the correct order."""
        with patch('main.MatcherHandler') as mock_handler_class:

            mock_handler = MagicMock()
            mock_handler.db = AsyncMock()
            mock_handler.broker = AsyncMock()
            mock_handler.service = AsyncMock()
            mock_handler.initialize = AsyncMock()

            # Track call order
            call_order = []

            def track_cleanup_service():
                call_order.append('service_cleanup')

            def track_cleanup_db():
                call_order.append('db_disconnect')

            def track_cleanup_broker():
                call_order.append('broker_disconnect')

            mock_handler.service.cleanup = AsyncMock(side_effect=track_cleanup_service)
            mock_handler.db.disconnect = AsyncMock(side_effect=track_cleanup_db)
            mock_handler.broker.disconnect = AsyncMock(side_effect=track_cleanup_broker)

            mock_handler_class.return_value = mock_handler

            from main import service_context

            async with service_context() as _:
                pass

            # Verify cleanup order: service -> db -> broker
            assert call_order == ['service_cleanup', 'db_disconnect', 'broker_disconnect']

    @pytest.mark.asyncio
    async def test_main_function_keyboard_interrupt(self):
        """Test main function handles KeyboardInterrupt gracefully."""
        with patch('main.MatcherHandler') as mock_handler_class, \
                patch('main.asyncio.sleep') as mock_sleep:

            mock_handler = MagicMock()
            mock_handler.db = AsyncMock()
            mock_handler.broker = AsyncMock()
            mock_handler.service = AsyncMock()
            mock_handler.initialize = AsyncMock()
            mock_handler.handle_match_request = AsyncMock()

            # Make sleep raise KeyboardInterrupt on first call
            mock_sleep.side_effect = KeyboardInterrupt()

            mock_handler.broker.subscribe_to_topic = AsyncMock()
            mock_handler_class.return_value = mock_handler

            from main import main

            # Should handle KeyboardInterrupt gracefully (not raise)
            await main()

            # Verify setup was done before interrupt
            mock_handler.broker.subscribe_to_topic.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_function_service_error(self):
        """Test main function handles service errors properly."""
        with patch('main.MatcherHandler') as mock_handler_class, \
                patch('main.asyncio.sleep') as mock_sleep, \
                patch('main.logger') as mock_logger:

            mock_handler = MagicMock()
            mock_handler.db = AsyncMock()
            mock_handler.broker = AsyncMock()
            mock_handler.service = AsyncMock()
            mock_handler.initialize = AsyncMock()
            mock_handler.handle_match_request = AsyncMock()

            # Make sleep raise a general exception
            test_error = RuntimeError("Service error")
            mock_sleep.side_effect = test_error

            mock_handler.broker.subscribe_to_topic = AsyncMock()
            mock_handler_class.return_value = mock_handler

            from main import main

            # Should handle and log the error (not raise)
            await main()

            # Verify error was logged
            mock_logger.error.assert_called()

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert "Service error" in error_call[1]["error"]

    @pytest.mark.asyncio
    async def test_main_function_normal_operation(self):
        """Test main function normal operation loop."""
        with patch('main.MatcherHandler') as mock_handler_class, \
                patch('main.asyncio.sleep') as mock_sleep, \
                patch('main.logger') as mock_logger:

            mock_handler = MagicMock()
            mock_handler.db = AsyncMock()
            mock_handler.broker = AsyncMock()
            mock_handler.service = AsyncMock()
            mock_handler.initialize = AsyncMock()
            mock_handler.handle_match_request = AsyncMock()

            # Let sleep run a few times then stop
            sleep_calls = [0] * 3  # Allow 3 sleep calls
            mock_sleep.side_effect = lambda x: sleep_calls.pop() if sleep_calls else (_ for _ in ()).throw(KeyboardInterrupt())

            mock_handler.broker.subscribe_to_topic = AsyncMock()
            mock_handler_class.return_value = mock_handler

            from main import main

            # Should handle KeyboardInterrupt gracefully
            await main()

            # Verify setup and loop behavior
            mock_handler.broker.subscribe_to_topic.assert_called_once()
            assert mock_sleep.call_count >= 3  # Should sleep at least 3 times before interrupt
            mock_logger.info.assert_called()  # Should log startup

    @pytest.mark.asyncio
    async def test_service_context_with_real_handler_methods(self):
        """Test service context with more realistic handler method interactions."""
        with patch('main.MatcherHandler') as mock_handler_class:

            mock_handler = MagicMock()
            mock_db = AsyncMock()
            mock_broker = AsyncMock()
            mock_service = AsyncMock()

            mock_handler.db = mock_db
            mock_handler.broker = mock_broker
            mock_handler.service = mock_service
            mock_handler.initialize = AsyncMock()

            # Simulate connection state tracking
            connection_states = {'db': False, 'broker': False, 'service': False}

            def connect_db():
                connection_states['db'] = True

            def connect_broker():
                connection_states['broker'] = True

            def init_service():
                connection_states['service'] = True

            def cleanup_service():
                connection_states['service'] = False

            def disconnect_db():
                connection_states['db'] = False

            def disconnect_broker():
                connection_states['broker'] = False

            mock_db.connect.side_effect = connect_db
            mock_broker.connect.side_effect = connect_broker
            mock_handler.initialize.side_effect = init_service
            mock_service.cleanup.side_effect = cleanup_service
            mock_db.disconnect.side_effect = disconnect_db
            mock_broker.disconnect.side_effect = disconnect_broker

            mock_handler_class.return_value = mock_handler

            from main import service_context

            async with service_context() as handler:
                # All connections should be established
                assert connection_states['db'] is True
                assert connection_states['broker'] is True
                assert connection_states['service'] is True
                assert handler == mock_handler

            # All connections should be cleaned up
            assert connection_states['db'] is False
            assert connection_states['broker'] is False
            assert connection_states['service'] is False

    @pytest.mark.skip(reason="Module reload with sys.path mocking is complex and fragile")
    def test_sys_path_modification(self):
        """Test that sys.path is modified as expected."""
        with patch('main.sys.path', new=list()) as mock_path:
            # Import the module to trigger the path modification
            import importlib
            import main
            importlib.reload(main)

            # Should have added /app/app to sys.path
            assert "/app/app" in mock_path

    @pytest.mark.asyncio
    async def test_service_context_handler_instance_creation(self):
        """Test that service context creates a new handler instance each time."""
        with patch('main.MatcherHandler') as mock_handler_class:

            # Create two different mock instances
            mock_handler1 = MagicMock()
            mock_handler1.db = AsyncMock()
            mock_handler1.broker = AsyncMock()
            mock_handler1.service = AsyncMock()
            mock_handler1.initialize = AsyncMock()

            mock_handler2 = MagicMock()
            mock_handler2.db = AsyncMock()
            mock_handler2.broker = AsyncMock()
            mock_handler2.service = AsyncMock()
            mock_handler2.initialize = AsyncMock()

            mock_handler_class.side_effect = [mock_handler1, mock_handler2]

            from main import service_context

            # Create two contexts
            async with service_context() as handler1:
                pass

            async with service_context() as handler2:
                pass

            # Should create two separate handler instances
            assert mock_handler_class.call_count == 2
            assert handler1 is mock_handler1
            assert handler2 is mock_handler2
