import json
import logging
from typing import List
from aio_pika import IncomingMessage, connect_robust, Message, ExchangeType
from common_py.logging_config import ContextLogger
from services.matcher.services.data_models import Product, VideoFrame, MatchResult
from services.matcher.services.matcher_service import matcher_service

# Initialize logger
logger = logging.getLogger(__name__)

# T022: Match Result Publisher
# Placeholder for configuration (will be loaded from config_loader.py later)
RABBITMQ_URL = "amqp://guest:guest@localhost/"
MATCH_RESULT_EXCHANGE = "pvm.match.result"

class MatchResultPublisher:
    """Manages the connection and publishing of match results."""
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        """Establishes connection and declares exchange."""
        if self.connection and not self.connection.is_closed:
            return
        
        self.connection = await connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            MATCH_RESULT_EXCHANGE, 
            ExchangeType.FANOUT, 
            durable=True
        )
        logger.info(f"MatchResultPublisher connected to {MATCH_RESULT_EXCHANGE} exchange.")

    async def publish(self, body: bytes):
        """Publishes the result message."""
        if not self.exchange:
            await self.connect() # Reconnect if necessary
        
        message = Message(
            body=body,
            content_type='application/json',
            delivery_mode=2 # Persistent
        )
        await self.exchange.publish(message, routing_key="")

# Global publisher instance
publisher = MatchResultPublisher()

async def handle_match_request(message: IncomingMessage):
    """
    Handles incoming RabbitMQ messages for product-video frame matching requests.
    """
    try:
        # 1. Parse the incoming message
        payload = json.loads(message.body.decode())
        
        # Assuming the payload contains data for both Product and VideoFrame
        product_data = payload.get("product")
        frame_data = payload.get("frame")
        
        if not product_data or not frame_data:
            logger.error("Invalid message format: missing 'product' or 'frame' data.", extra={"payload": payload})
            message.reject(requeue=False)
            return

        # 2. Validate and create data models
        # Note: Pydantic validation handles missing/incorrect fields
        product = Product(**product_data)
        frame = VideoFrame(**frame_data)
        
        # 3. Perform the matching
        match_results: List[MatchResult] = matcher_service.match(product, frame)
        
        # 4. Prepare the output message (for T022)
        output_payload = {
            "product_id": product.product_id,
            "frame_id": frame.frame_id,
            "matches": [result.model_dump() for result in match_results]
        }
        
        # 5. Publish the result (T022)
        await publisher.publish(output_body)
        
        logger.info(f"Match request processed and result published. Found {len(match_results)} matches.", extra={"product_id": product.product_id, "frame_id": frame.frame_id})
        
        message.ack()

    except json.JSONDecodeError:
        logger.error("Failed to decode JSON message.", exc_info=True)
        message.reject(requeue=False)
    except Exception as e:
        logger.error(f"An unexpected error occurred during message handling: {e}", exc_info=True)
        message.reject(requeue=False)