import asyncio
import os
import uuid
import pytest
from support.message_spy import CollectionPhaseSpy
from support.event_publisher import CollectionEventPublisher
from common_py.messaging import MessageBroker

class TestDebugSpy:
    @pytest.mark.asyncio
    async def test_debug_spy_capture(self):
        broker_url = os.getenv('BROKER_URL', 'amqp://guest:guest@localhost:5672/')

        # Create spy
        spy = CollectionPhaseSpy(broker_url)
        await spy.connect()

        # Create event publisher
        broker = MessageBroker(broker_url)
        await broker.connect()
        publisher = CollectionEventPublisher(broker)

        # Publish a test video completion event manually
        job_id = 'debug_job_123'
        correlation_id = str(uuid.uuid4())

        print(f'Publishing test event with correlation_id: {correlation_id}')

        event_id = await publisher.publish_mock_videos_collections_completed(job_id, correlation_id)
        print(f'Published event_id: {event_id}')

        # Wait a moment
        await asyncio.sleep(2)

        # Check captured messages
        videos_msgs = spy.spy.get_captured_messages(spy.videos_queue)
        print(f'Videos messages captured: {len(videos_msgs)}')

        for msg in videos_msgs:
            print(f'  Routing: {msg.get("routing_key")}, Correlation: {msg.get("correlation_id")}, Job: {msg.get("event_data", {}).get("job_id")}')

        # Also check correlation-specific messages
        correlation_msgs = spy.spy.get_captured_messages_by_correlation_id(spy.videos_queue, correlation_id)
        print(f'Messages with correlation_id {correlation_id}: {len(correlation_msgs)}')

        # Assertions
        assert len(videos_msgs) == 1, f"Expected 1 message, got {len(videos_msgs)}"
        assert len(correlation_msgs) == 1, f"Expected 1 message with correlation_id, got {len(correlation_msgs)}"

        msg = videos_msgs[0]
        assert msg.get("routing_key") == "videos.collections.completed"
        assert msg.get("correlation_id") == correlation_id
        assert msg.get("event_data", {}).get("job_id") == job_id

        await spy.disconnect()
        await broker.disconnect()