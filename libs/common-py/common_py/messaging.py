import asyncio
import json
import uuid
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timezone
import aio_pika
from aio_pika import Message, DeliveryMode
from .logging_config import configure_logging
from .messaging_handler import MessageHandler # New import

logger = configure_logging("common-py:messaging")


class MessageBroker:
    """RabbitMQ message broker wrapper"""
    
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.connection = None
        self.channel = None
        self.exchange = None
        self.message_handler_instance = None # New instance
    
    async def connect(self, timeout: float = 30.0):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = await asyncio.wait_for(
                aio_pika.connect_robust(self.broker_url),
                timeout=timeout
            )
            self.channel = await self.connection.channel()
            
            # Declare main exchange
            self.exchange = await self.channel.declare_exchange(
                "product_video_matching",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info("Connected to RabbitMQ", broker_url=self.broker_url)
            
        except Exception as e:
            logger.error("Failed to connect to RabbitMQ", error=str(e))
            raise
    
    async def disconnect(self):
        """Close connection to RabbitMQ"""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def publish_event(self, topic: str, event_data: Dict[str, Any], correlation_id: Optional[str] = None):
        """
        Publish an event to a topic
        
        Args:
            topic: The topic to publish to (e.g., 'products.collect.request')
            event_data: The event data
            correlation_id: Optional correlation ID for tracing
        """
        if not self.exchange:
            raise RuntimeError("Not connected to RabbitMQ")
        
        # Add metadata
        enriched_event = {
            **event_data,
            "_metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id or str(uuid.uuid4()),
                "topic": topic
            }
        }
        
        message = Message(
            json.dumps(enriched_event).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=enriched_event["_metadata"]["correlation_id"]
        )
        
        await self.exchange.publish(message, routing_key=topic)
        
        logger.info(
            "Published event",
            topic=topic,
            correlation_id=enriched_event["_metadata"]["correlation_id"]
        )
    
    async def subscribe_to_topic(self, topic: str, handler: Callable, queue_name: Optional[str] = None):
        """
        Subscribe to a topic and handle messages
        
        Args:
            topic: The topic to subscribe to
            handler: Async function to handle messages
            queue_name: Optional queue name (defaults to topic-based name)
        """
        if not self.exchange:
            raise RuntimeError("Not connected to RabbitMQ")
        
        # Create queue
        queue_name = queue_name or f"queue.{topic}"
        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        # Bind queue to topic
        await queue.bind(self.exchange, routing_key=topic)
        
        # Set up DLQ
        dlq_name = f"{queue_name}.dlq"
        dlq = await self.channel.declare_queue(dlq_name, durable=True)
        
        # Create a dedicated MessageHandler for this subscription to ensure correct DLQ routing
        message_handler = MessageHandler(self.exchange, dlq_name)

        # Start consuming with a handler bound to this subscription's DLQ
        await queue.consume(lambda message: message_handler.handle_message(message, handler, topic))
        
        logger.info(
            "Subscribed to topic",
            topic=topic,
            queue=queue_name
        )

    async def get_queue_message_count(self, queue_name: str) -> int:
        """
        Get the number of messages in a queue

        Args:
            queue_name: Name of the queue to check

        Returns:
            Number of messages in the queue
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")

        try:
            # Declare queue to ensure it exists (passive=True means just check)
            queue = await self.channel.declare_queue(queue_name, durable=True, passive=True)
            return queue.declaration_result.message_count
        except Exception as e:
            logger.error("Failed to get queue message count", queue_name=queue_name, error=str(e))
            raise
