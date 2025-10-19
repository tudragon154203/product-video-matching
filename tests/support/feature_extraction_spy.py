"""
Feature Extraction Phase Message Spy
Spy for RabbitMQ messages during feature extraction phase integration tests.
"""
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

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
            "video_keypoints_completed": []
        }
        self.queues: Dict[str, str] = {}
        self.queue_namespaces: Dict[str, str] = {}

    async def connect(self):
        """Connect to message broker and set up spy queues"""
        await self.broker.connect()

        # Create namespaced spy queues for each event type
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Set up queues with auto-delete and namespacing
        queue_configs = [
            ("products_images_masked_batch", "image.masking.completed"),
            ("video_keyframes_masked_batch", "video.masking.completed"),
            ("image_embeddings_completed", "image.embeddings.completed"),
            ("image_keypoints_completed", "image.keypoints.completed"),
            ("video_keypoints_completed", "video.keypoints.completed")
        ]

        for queue_name, routing_key in queue_configs:
            namespaced_queue = f"test_feat_ext_{queue_name}_{timestamp}"

            # Declare queue with auto-delete
            await self.broker.channel.queue_declare(
                queue=namespaced_queue,
                durable=False,
                auto_delete=True,
                arguments={"x-message-ttl": 300000}  # 5 minutes TTL
            )

            # Bind to topic exchange
            await self.broker.channel.queue_bind(
                queue=namespaced_queue,
                exchange="pvm_events",
                routing_key=routing_key
            )

            # Start consuming
            await self.broker.channel.basic_consume(
                queue=namespaced_queue,
                on_message_callback=self._create_callback(queue_name)
            )

            self.queues[queue_name] = namespaced_queue
            self.queue_namespaces[namespaced_queue] = queue_name

    def _create_callback(self, event_type: str):
        """Create message callback for specific event type"""
        async def callback(ch, method, properties, body):
            try:
                message = json.loads(body.decode('utf-8'))
                captured_message = {
                    "event_data": message,
                    "routing_key": method.routing_key,
                    "timestamp": datetime.utcnow().isoformat(),
                    "headers": dict(properties.headers or {}),
                    "correlation_id": properties.headers.get("correlation_id") if properties.headers else None
                }
                self.captured_messages[event_type].append(captured_message)
                await ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"Error processing message in {event_type} spy: {e}")
                await ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

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
        """Disconnect and clean up queues"""
        try:
            # Delete queues
            for queue_name in self.queues.values():
                try:
                    await self.broker.channel.queue_delete(queue=queue_name)
                except Exception as e:
                    print(f"Error deleting queue {queue_name}: {e}")

            await self.broker.disconnect()
        except Exception as e:
            print(f"Error during disconnect: {e}")

    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'broker') and self.broker:
            try:
                asyncio.create_task(self.disconnect())
            except Exception:
                pass  # Event loop might be closed