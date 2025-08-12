import asyncio
import json
import uuid
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import aio_pika
from aio_pika import Message, DeliveryMode
import structlog

logger = structlog.get_logger()


class MessageBroker:
    """RabbitMQ message broker wrapper"""
    
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.connection = None
        self.channel = None
        self.exchange = None
    
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
                "timestamp": datetime.utcnow().isoformat(),
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
        
        async def message_handler(message: aio_pika.IncomingMessage):
            correlation_id = message.correlation_id
            
            try:
                # Parse message
                event_data = json.loads(message.body.decode())
                
                logger.info(
                    "Received event",
                    topic=topic,
                    correlation_id=correlation_id
                )
                
                # Call handler
                await handler(event_data)
                
                # Acknowledge message
                await message.ack()
                
                logger.info(
                    "Processed event successfully",
                    topic=topic,
                    correlation_id=correlation_id
                )
                
            except Exception as e:
                logger.error(
                    "Failed to process event",
                    topic=topic,
                    correlation_id=correlation_id,
                    error=str(e)
                )
                
                # Import error handling
                from .error_codes import ErrorCode, create_error
                
                # Determine if error is retryable
                is_retryable = self._is_retryable_error(e)
                
                # Check retry count
                retry_count = message.headers.get("x-retry-count", 0) if message.headers else 0
                
                if is_retryable and retry_count < 3:
                    # Retry with exponential backoff
                    delay = min(2 ** retry_count, 60)  # Max 60 seconds
                    
                    await asyncio.sleep(delay)
                    
                    # Republish with incremented retry count
                    retry_message = Message(
                        message.body,
                        headers={
                            "x-retry-count": retry_count + 1,
                            "x-error-type": type(e).__name__,
                            "x-last-error": str(e)[:500]  # Truncate long errors
                        },
                        correlation_id=correlation_id
                    )
                    
                    await self.exchange.publish(retry_message, routing_key=topic)
                    await message.ack()
                    
                    logger.info(
                        "Retrying event",
                        topic=topic,
                        correlation_id=correlation_id,
                        retry_count=retry_count + 1,
                        delay_seconds=delay
                    )
                else:
                    # Send to DLQ
                    dlq_message = Message(
                        message.body,
                        headers={
                            "x-original-topic": topic, 
                            "x-failure-reason": str(e)[:500],
                            "x-error-type": type(e).__name__,
                            "x-retry-count": retry_count,
                            "x-is-retryable": str(is_retryable)
                        },
                        correlation_id=correlation_id
                    )
                    
                    await self.exchange.publish(dlq_message, routing_key=dlq_name)
                    await message.ack()
                    
                    logger.error(
                        "Event sent to DLQ",
                        topic=topic,
                        correlation_id=correlation_id,
                        dlq=dlq_name,
                        retry_count=retry_count,
                        is_retryable=is_retryable,
                        reason="max_retries" if is_retryable else "fatal_error"
                    )
        
        # Start consuming
        await queue.consume(message_handler)
        
        logger.info(
            "Subscribed to topic",
            topic=topic,
            queue=queue_name
        )
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable"""
        # Import here to avoid circular imports
        from .error_codes import RetryableError, ErrorCode
        
        if isinstance(error, RetryableError):
            return True
        
        # Check for common retryable error types
        retryable_types = [
            "ConnectionError",
            "TimeoutError", 
            "HTTPStatusError",
            "NetworkError",
            "TemporaryFailure"
        ]
        
        error_type = type(error).__name__
        return any(retryable in error_type for retryable in retryable_types)