import asyncio
from typing import Dict, Any, List, Callable
from .logging_config import configure_logging
from .metrics import metrics
from .monitoring.health_monitor import HealthMonitor
from .monitoring.metrics_exporter import MetricsExporter
from .monitoring.alert_handlers import log_alert_handler, console_alert_handler

logger = configure_logging("common-py:monitoring")

# Global monitoring instance
monitor = None


def get_monitor(service_name: str) -> HealthMonitor:
    """Get or create global monitor instance"""
    global monitor
    if not monitor:
        monitor = HealthMonitor(service_name)
        monitor.add_alert_handler(log_alert_handler)
        monitor.add_alert_handler(console_alert_handler)
    return monitor
