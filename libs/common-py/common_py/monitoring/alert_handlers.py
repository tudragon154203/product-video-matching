import asyncio
from typing import Dict, Any
from ..logging_config import configure_logging

logger = configure_logging("common-py")

async def log_alert_handler(alert: Dict[str, Any]):
    """Log alert to structured logger"""
    logger.warning("Health alert", **alert)


async def console_alert_handler(alert: Dict[str, Any]):
    """Print alert to console"""
    print(f"ALERT [{alert['type'].upper()}] {alert['service']}: {alert['message']}")
