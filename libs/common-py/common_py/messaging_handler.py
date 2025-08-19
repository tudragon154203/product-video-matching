import asyncio
import json
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import aio_pika
from aio_pika import Message, DeliveryMode

from .logging_config import configure_logging
from .error_codes import ErrorCode, create_error, RetryableError

logger = configure_logging("common-py")

class MessageHandler:
    def __init__(self, broker_exchange: aio_pika.Exchange, dlq_name: str):
        self.exchange = broker_exchange
        self.dlq_name = dlq_name

    async def handle_message(self, message: aio_pika.IncomingMessage, handler: Callable, topic: str):
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
                
                await self.exchange.publish(dlq_message, routing_key=self.dlq_name)
                await message.ack()
                
                logger.error(
                    "Event sent to DLQ",
                    topic=topic,
                    correlation_id=correlation_id,
                    dlq=self.dlq_name,
                    retry_count=retry_count,
                    is_retryable=is_retryable,
                    reason="max_retries" if is_retryable else "fatal_error"
                )
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable"""
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
