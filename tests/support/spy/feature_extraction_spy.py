"""
Feature Extraction Phase Message Spy
Spy for RabbitMQ messages during feature extraction phase integration tests.
"""
import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime, timezone

from common_py.messaging import MessageBroker


class FeatureExtractionSpy:
    """
    Spy for feature extraction phase messages.
    Tracks products_images_masked_batch, video_keyframes_masked_batch,
    image_embeddings_completed, image_keypoints_completed, and video_keypoints_completed events.
    """

    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.broker = MessageBroker(broker_url)
        self.captured_messages: Dict[str, List[Dict]] = {
            "products_images_masked_batch": [],
            "video_keyframes_masked_batch": [],
            "image_embeddings_completed": [],
            "image_keypoints_completed": [],
            "video_keypoints_completed": [],
            "match_request": []
        }
        self.queues: Dict[str, str] = {}
        self.queue_namespaces: Dict[str, str] = {}

    async def connect(self):
        """Connect to message broker and set up spy queues"""
        await self.broker.connect()

        # Create namespaced spy queues for each event type
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Set up queues with auto-delete and namespacing
        queue_configs = [
            ("products_images_masked_batch", "products.images.masked.batch"),
            ("video_keyframes_masked_batch", "video.keyframes.masked.batch"),
            ("image_embeddings_completed", "image.embeddings.completed"),
            ("image_keypoints_completed", "image.keypoints.completed"),
            ("video_keypoints_completed", "video.keypoints.completed"),
            ("match_request", "match.request")
        ]

        for queue_name, routing_key in queue_configs:
            # Add UUID for uniqueness to avoid conflicts
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            namespaced_queue = f"test_feat_ext_{queue_name}_{timestamp}_{unique_id}"

            # Declare queue with auto-delete and TTL
            queue = await self.broker.channel.declare_queue(
                namespaced_queue,
                durable=False,
                auto_delete=True,
                arguments={"x-message-ttl": 300000}  # 5 minutes TTL
            )

            # Bind to topic exchange
            await queue.bind(self.broker.exchange, routing_key=routing_key)

            # Start consuming
            await queue.consume(self._create_callback(queue_name))

            self.queues[queue_name] = namespaced_queue
            self.queue_namespaces[namespaced_queue] = queue_name

    def _create_callback(self, event_type: str):
        """Create message callback for specific event type"""
        async def callback(message):
            try:
                # Decode the message body
                body = json.loads(message.body.decode('utf-8'))
                captured_message = {
                    "event_data": body,
                    "routing_key": message.routing_key,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "headers": dict(message.headers or {}),
                    "correlation_id": message.correlation_id
                }
                self.captured_messages[event_type].append(captured_message)
                await message.ack()
            except Exception as e:
                print(f"Error processing message in {event_type} spy: {e}")
                await message.nack(requeue=False)

        return callback

    async def wait_for_products_images_masked(self, job_id: str, timeout: float = 300.0) -> Dict[str, Any]:
        """Wait for products_images_masked_batch event"""
        return await self._wait_for_event("products_images_masked_batch", job_id, timeout)

    async def wait_for_video_keyframes_masked(self, job_id: str, timeout: float = 300.0) -> Dict[str, Any]:
        """Wait for video_keyframes_masked_batch event"""
        return await self._wait_for_event("video_keyframes_masked_batch", job_id, timeout)

    async def wait_for_image_embeddings_completed(self, job_id: str, timeout: float = 300.0) -> Dict[str, Any]:
        """Wait for image_embeddings_completed event"""
        return await self._wait_for_event("image_embeddings_completed", job_id, timeout)

    async def wait_for_image_keypoints_completed(self, job_id: str, timeout: float = 300.0) -> Dict[str, Any]:
        """Wait for image_keypoints_completed event"""
        return await self._wait_for_event("image_keypoints_completed", job_id, timeout)

    async def wait_for_video_keypoints_completed(self, job_id: str, timeout: float = 300.0) -> Dict[str, Any]:
        """Wait for video_keypoints_completed event"""
        return await self._wait_for_event("video_keypoints_completed", job_id, timeout)

    async def wait_for_match_request(self, job_id: str, timeout: float = 300.0) -> Dict[str, Any]:
        """Wait for match_request event"""
        return await self._wait_for_event("match_request", job_id, timeout)

    async def _wait_for_event(self, event_type: str, job_id: str, timeout: float) -> Dict[str, Any]:
        """Wait for specific event type for given job_id"""
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            for message in self.captured_messages[event_type]:
                if message["event_data"].get("job_id") == job_id:
                    return message
            await asyncio.sleep(0.5)

        raise TimeoutError(f"Expected {event_type} event for job_id {job_id} not received within {timeout}s")

    def clear_messages(self):
        """Clear all captured messages"""
        for key in self.captured_messages:
            self.captured_messages[key] = []

    @staticmethod
    async def cleanup_orphaned_queues(broker_url: str):
        """Clean up old test queues that might still exist"""
        try:
            broker = MessageBroker(broker_url)
            await broker.connect()

            # Get all queues and clean up old test queues
            channel = await broker.connection.channel()
            await channel.queue_declare(queue="", passive=True, durable=False)

            # Try to delete the old orphaned queue if it exists
            try:
                old_queue = await channel.queue_declare(
                    queue="test_feat_ext_products_images_masked_batch_20251019_074126",
                    passive=True
                )
                await old_queue.delete()
                print("Deleted orphaned queue: test_feat_ext_products_images_masked_batch_20251019_074126")
            except Exception:
                # Queue doesn't exist or can't be deleted, that's fine
                pass

            await broker.disconnect()
        except Exception as e:
            print(f"Error cleaning up orphaned queues: {e}")

    def get_captured_messages_by_correlation_id(self, event_type: str, correlation_id: str) -> List[Dict]:
        """Get captured messages for specific correlation_id"""
        return [
            msg for msg in self.captured_messages[event_type]
            if msg.get("correlation_id") == correlation_id
        ]

    def get_all_captured_messages(self, event_type: str) -> List[Dict]:
        """Get all captured messages for event type"""
        return self.captured_messages[event_type].copy()

    def count_captured_messages(self, event_type: str) -> int:
        """Count captured messages for event type"""
        return len(self.captured_messages[event_type])

    async def disconnect(self):
        """Disconnect and rely on auto_delete for queue cleanup"""
        try:
            # Don't try to delete queues - they have auto_delete=True and TTL
            # This avoids the "precondition_failed: queue in use" errors
            await self.broker.disconnect()
        except Exception:
            # Silently ignore disconnect errors
            pass

    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'broker') and self.broker:
            try:
                asyncio.create_task(self.disconnect())
            except Exception:
                pass  # Event loop might be closed
