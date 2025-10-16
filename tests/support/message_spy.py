"""
Message broker spy utilities for RabbitMQ integration testing.
Provides ephemeral spy queues for event capture and validation.
"""
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import aio_pika
from aio_pika import Message, DeliveryMode

from common_py.logging_config import configure_logging

logger = configure_logging("test-utils:message-spy")


class MessageSpy:
    """
    RabbitMQ message spy for capturing events during integration tests.
    Creates ephemeral queues bound to specific routing keys.
    """
    
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.connection = None
        self.channel = None
        self.exchange = None
        self.spy_queues = {}
        self.captured_messages = {}
        self.consumers = {}
        
    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(self.broker_url)
            self.channel = await self.connection.channel()
            
            # Declare main exchange
            self.exchange = await self.channel.declare_exchange(
                "product_video_matching",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("Message spy connected to RabbitMQ", broker_url=self.broker_url)
            
        except Exception as e:
            logger.error("Failed to connect message spy to RabbitMQ", error=str(e))
            raise
    
    async def disconnect(self):
        """Close connection and clean up spy queues"""
        # Cancel all consumers - remove queue bindings instead
        for queue_name, queue in self.spy_queues.items():
            try:
                await queue.unbind(self.exchange, routing_key=queue_name.replace("spy.", "").replace("_", "."))
                logger.info("Unbound spy queue", queue_name=queue_name)
            except Exception as e:
                logger.warning("Failed to unbind spy queue", queue_name=queue_name, error=str(e))
        
        # Delete spy queues
        for queue_name, queue in self.spy_queues.items():
            try:
                await queue.delete()
                logger.info("Deleted spy queue", queue=queue_name)
            except Exception as e:
                logger.warning("Failed to delete spy queue", queue=queue_name, error=str(e))
        
        if self.connection:
            await self.connection.close()
            logger.info("Message spy disconnected from RabbitMQ")
    
    async def create_spy_queue(self, routing_key: str, queue_name: Optional[str] = None) -> str:
        """
        Create an ephemeral spy queue bound to a routing key
        
        Args:
            routing_key: The routing key to spy on (e.g., 'products.collections.completed')
            queue_name: Optional custom queue name (auto-generated if not provided)
            
        Returns:
            The queue name
        """
        if not self.exchange:
            raise RuntimeError("Message spy not connected to RabbitMQ")
        
        # Generate unique queue name if not provided
        if not queue_name:
            queue_name = f"spy.{routing_key.replace('.', '_')}.{uuid.uuid4().hex[:8]}"
        
        # Create ephemeral queue (auto-delete)
        queue = await self.channel.declare_queue(
            queue_name,
            durable=False,  # Non-durable
            auto_delete=True,  # Auto-delete when consumer disconnects
            exclusive=False  # Allow multiple connections
        )
        
        # Bind queue to routing key
        await queue.bind(self.exchange, routing_key=routing_key)
        
        # Initialize captured messages list
        self.captured_messages[queue_name] = []
        
        # Store queue reference
        self.spy_queues[queue_name] = queue
        
        logger.info(
            "Created spy queue",
            queue_name=queue_name,
            routing_key=routing_key
        )
        
        return queue_name
    
    async def start_consuming(self, queue_name: str, timeout: float = 10.0):
        """
        Start consuming messages from a spy queue
        
        Args:
            queue_name: The spy queue name
            timeout: Timeout in seconds for message processing
        """
        if queue_name not in self.spy_queues:
            raise ValueError(f"Spy queue {queue_name} not found")
        
        queue = self.spy_queues[queue_name]
        
        async def message_handler(message: aio_pika.IncomingMessage):
            try:
                async with message.process():
                    # Parse message body
                    raw_body = message.body.decode()
                    event_data = json.loads(raw_body)

                    # Add metadata
                    enriched_message = {
                        "event_data": event_data,
                        "routing_key": message.routing_key,
                        "correlation_id": message.correlation_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "headers": dict(message.headers) if message.headers else {}
                    }

                    # Store captured message
                    self.captured_messages[queue_name].append(enriched_message)

                    logger.debug(
                        "Captured message",
                        queue_name=queue_name,
                        routing_key=message.routing_key,
                        correlation_id=message.correlation_id
                    )
                
            except Exception as e:
                logger.error(
                    "Failed to process spy message",
                    queue_name=queue_name,
                    error=str(e)
                )
        
        # Start consuming with timeout
        consumer_tag = await queue.consume(message_handler)
        self.consumers[queue_name] = consumer_tag
        
        logger.info(
            "Started consuming from spy queue",
            queue_name=queue_name,
            consumer_tag=consumer_tag
        )
    
    async def stop_consuming(self, queue_name: str):
        """Stop consuming messages from a spy queue"""
        if queue_name in self.consumers and queue_name in self.spy_queues:
            queue = self.spy_queues[queue_name]
            try:
                await queue.cancel()
                logger.info("Cancelled consuming from spy queue", queue_name=queue_name)
            except Exception as e:
                logger.warning("Failed to cancel consuming from spy queue", queue_name=queue_name, error=str(e))
            finally:
                del self.consumers[queue_name]
            
            logger.info(
                "Stopped consuming from spy queue",
                queue_name=queue_name,
                consumer_tag=consumer_tag
            )
    
    def get_captured_messages(self, queue_name: str) -> List[Dict[str, Any]]:
        """Get all captured messages from a spy queue"""
        return self.captured_messages.get(queue_name, [])
    
    def get_captured_messages_by_correlation_id(self, queue_name: str, correlation_id: str) -> List[Dict[str, Any]]:
        """Get captured messages filtered by correlation ID"""
        messages = self.captured_messages.get(queue_name, [])
        return [msg for msg in messages if msg.get("correlation_id") == correlation_id]
    
    def clear_captured_messages(self, queue_name: str):
        """Clear captured messages for a spy queue"""
        if queue_name in self.captured_messages:
            self.captured_messages[queue_name].clear()
            logger.info("Cleared captured messages", queue_name=queue_name)
    
    async def wait_for_message(
        self, 
        queue_name: str, 
        correlation_id: Optional[str] = None,
        timeout: float = 10.0,
        predicate: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for a specific message to arrive
        
        Args:
            queue_name: The spy queue name
            correlation_id: Optional correlation ID to wait for
            timeout: Timeout in seconds
            predicate: Optional predicate function to match messages
            
        Returns:
            The matching message or None if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            messages = self.captured_messages.get(queue_name, [])
            
            for message in messages:
                # Check correlation ID filter
                if correlation_id and message.get("correlation_id") != correlation_id:
                    continue
                
                # Check predicate filter
                if predicate and not predicate(message):
                    continue
                
                return message
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
        
        logger.warning(
            "Timeout waiting for message",
            queue_name=queue_name,
            correlation_id=correlation_id,
            timeout=timeout
        )
        return None
    
    async def assert_message_received(
        self,
        queue_name: str,
        correlation_id: Optional[str] = None,
        timeout: float = 10.0,
        expected_event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assert that a message was received and return it
        
        Args:
            queue_name: The spy queue name
            correlation_id: Optional correlation ID to wait for
            timeout: Timeout in seconds
            expected_event_type: Optional expected event type in routing key
            
        Returns:
            The matching message
            
        Raises:
            AssertionError: If message not received within timeout
        """
        predicate = None
        if expected_event_type:
            predicate = lambda msg: expected_event_type in msg.get("routing_key", "")
        
        message = await self.wait_for_message(
            queue_name=queue_name,
            correlation_id=correlation_id,
            timeout=timeout,
            predicate=predicate
        )
        
        if not message:
            raise AssertionError(
                f"Expected message not received in queue {queue_name}"
                f"{' for correlation_id ' + correlation_id if correlation_id else ''}"
                f"{' with event type ' + expected_event_type if expected_event_type else ''}"
                f" within {timeout}s"
            )
        
        return message


class CollectionPhaseSpy:
    """
    Specialized message spy for collection phase integration tests.
    Sets up spy queues for products and videos collection completed events.
    """
    
    def __init__(self, broker_url: str):
        self.spy = MessageSpy(broker_url)
        self.products_queue = None
        self.videos_queue = None
        
    async def connect(self):
        """Connect and set up spy queues for collection phase"""
        await self.spy.connect()
        
        # Create spy queues for collection completed events
        self.products_queue = await self.spy.create_spy_queue("products.collections.completed")
        self.videos_queue = await self.spy.create_spy_queue("videos.collections.completed")
        
        # Start consuming
        await self.spy.start_consuming(self.products_queue)
        await self.spy.start_consuming(self.videos_queue)
        
        logger.info("Collection phase spy connected and ready")
    
    async def disconnect(self):
        """Disconnect and clean up"""
        await self.spy.disconnect()
        logger.info("Collection phase spy disconnected")
    
    async def wait_for_products_completed(
        self, 
        job_id: str, 
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Wait for products collection completed event"""
        message = await self.spy.assert_message_received(
            queue_name=self.products_queue,
            timeout=timeout,
            expected_event_type="products.collections.completed"
        )
        
        # Verify job ID matches
        if message["event_data"].get("job_id") != job_id:
            raise AssertionError(
                f"Expected job_id {job_id}, got {message['event_data'].get('job_id')}"
            )
        
        return message
    
    async def wait_for_videos_completed(
        self, 
        job_id: str, 
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Wait for videos collection completed event"""
        message = await self.spy.assert_message_received(
            queue_name=self.videos_queue,
            timeout=timeout,
            expected_event_type="videos.collections.completed"
        )
        
        # Verify job ID matches
        if message["event_data"].get("job_id") != job_id:
            raise AssertionError(
                f"Expected job_id {job_id}, got {message['event_data'].get('job_id')}"
            )
        
        return message
    
    async def wait_for_both_completed(
        self, 
        job_id: str, 
        timeout: float = 20.0
    ) -> Dict[str, Dict[str, Any]]:
        """Wait for both products and videos collection completed events"""
        # Wait for both events concurrently
        products_task = asyncio.create_task(
            self.wait_for_products_completed(job_id, timeout)
        )
        videos_task = asyncio.create_task(
            self.wait_for_videos_completed(job_id, timeout)
        )
        
        try:
            products_message, videos_message = await asyncio.gather(
                products_task, videos_task
            )
            
            return {
                "products": products_message,
                "videos": videos_message
            }
        except Exception as e:
            # Cancel pending tasks
            products_task.cancel()
            videos_task.cancel()
            raise
    
    def clear_messages(self):
        """Clear all captured messages"""
        if self.products_queue:
            self.spy.clear_captured_messages(self.products_queue)
        if self.videos_queue:
            self.spy.clear_captured_messages(self.videos_queue)