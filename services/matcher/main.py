import asyncio
import logging
from aio_pika import connect_robust, ExchangeType
from common_py.logging_config import configure_logging
from handlers.match_request_handler import handle_match_request

# 1. Configure Logging (T023 - Part 1)
configure_logging()
logger = logging.getLogger(__name__)

# Placeholder for configuration (will be loaded from config_loader.py later)
RABBITMQ_URL = "amqp://guest:guest@localhost/"
MATCH_REQUEST_QUEUE = "match_requests"
MATCH_REQUEST_EXCHANGE = "pvm.match.request"


async def main():
    """
    Main function to connect to RabbitMQ and start consuming messages. (T021)
    """
    logger.info("Starting Matcher Microservice...")

    try:
        # Connect to RabbitMQ
        connection = await connect_robust(RABBITMQ_URL)

        # Creating a channel
        channel = await connection.channel()

        # Declare the exchange (assuming a fanout or direct exchange for requests)
        exchange = await channel.declare_exchange(
            MATCH_REQUEST_EXCHANGE,
            ExchangeType.FANOUT,
            durable=True
        )

        # Declare the queue and bind it to the exchange
        queue = await channel.declare_queue(
            MATCH_REQUEST_QUEUE,
            durable=True
        )
        await queue.bind(exchange, routing_key="")  # Bind to fanout exchange

        # Start consuming messages
        logger.info(f"Waiting for messages on queue: {MATCH_REQUEST_QUEUE}")
        await queue.consume(handle_match_request)

        # Keep the main task running
        await asyncio.Future()

    except Exception as e:
        logger.critical(f"Fatal error in main loop: {e}", exc_info=True)
    finally:
        if 'connection' in locals() and connection:
            await connection.close()
        logger.info("Matcher Microservice stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user.")
