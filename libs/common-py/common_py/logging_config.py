import structlog
import logging
import sys
from typing import Any


def configure_logging(service_name: str, log_level: str = "INFO"):
    """Configure logging for the service"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Get and configure the logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    return logger