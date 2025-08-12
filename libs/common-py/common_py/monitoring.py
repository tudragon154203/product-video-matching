"""
Monitoring and alerting utilities
"""
import asyncio
from typing import Dict, Any, List, Callable
import structlog
from .metrics import metrics

logger = structlog.get_logger()


class HealthMonitor:
    """Monitor service health and trigger alerts"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.health_checks = {}
        self.alert_handlers = []
        self.monitoring_task = None
        self.check_interval = 30  # seconds
    
    def add_health_check(self, name: str, check_func: Callable, critical: bool = False):
        """Add a health check"""
        self.health_checks[name] = {
            "func": check_func,
            "critical": critical,
            "last_result": None,
            "failure_count": 0
        }
    
    def add_alert_handler(self, handler: Callable):
        """Add an alert handler function"""
        self.alert_handlers.append(handler)
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        if self.monitoring_task:
            return
        
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started", service=self.service_name)
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        logger.info("Health monitoring stopped", service=self.service_name)
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await self._run_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in monitoring loop", error=str(e))
                await asyncio.sleep(self.check_interval)
    
    async def _run_health_checks(self):
        """Run all health checks"""
        overall_healthy = True
        
        for check_name, check_info in self.health_checks.items():
            try:
                result = await check_info["func"]()
                
                if result:
                    # Health check passed
                    if check_info["failure_count"] > 0:
                        # Recovery from failure
                        await self._send_alert(
                            "recovery",
                            f"Health check '{check_name}' recovered",
                            {"check": check_name, "service": self.service_name}
                        )
                    
                    check_info["failure_count"] = 0
                    check_info["last_result"] = True
                    
                    # Record metric
                    metrics.set_gauge(
                        f"health_check_{check_name}",
                        1.0,
                        {"service": self.service_name}
                    )
                else:
                    # Health check failed
                    check_info["failure_count"] += 1
                    check_info["last_result"] = False
                    overall_healthy = False
                    
                    # Record metric
                    metrics.set_gauge(
                        f"health_check_{check_name}",
                        0.0,
                        {"service": self.service_name}
                    )
                    
                    # Send alert if critical or multiple failures
                    if check_info["critical"] or check_info["failure_count"] >= 3:
                        await self._send_alert(
                            "failure",
                            f"Health check '{check_name}' failed",
                            {
                                "check": check_name,
                                "service": self.service_name,
                                "failure_count": check_info["failure_count"],
                                "critical": check_info["critical"]
                            }
                        )
                
            except Exception as e:
                logger.error("Health check failed with exception", 
                           check=check_name, error=str(e))
                
                check_info["failure_count"] += 1
                check_info["last_result"] = False
                overall_healthy = False
                
                metrics.set_gauge(
                    f"health_check_{check_name}",
                    0.0,
                    {"service": self.service_name}
                )
        
        # Record overall health
        metrics.set_gauge(
            "service_healthy",
            1.0 if overall_healthy else 0.0,
            {"service": self.service_name}
        )
    
    async def _send_alert(self, alert_type: str, message: str, details: Dict[str, Any]):
        """Send alert to all handlers"""
        alert = {
            "type": alert_type,
            "service": self.service_name,
            "message": message,
            "details": details,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error("Alert handler failed", handler=str(handler), error=str(e))


class MetricsExporter:
    """Export metrics in various formats"""
    
    @staticmethod
    def to_prometheus_format() -> str:
        """Export metrics in Prometheus format"""
        lines = []
        current_metrics = metrics.get_metrics()
        
        # Export counters
        for name, value in current_metrics["counters"].items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Export gauges
        for name, value in current_metrics["gauges"].items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # Export histograms
        for name, stats in current_metrics["histograms"].items():
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_count {stats['count']}")
            lines.append(f"{name}_sum {stats['avg'] * stats['count']}")
            lines.append(f"{name}_bucket{{le=\"0.1\"}} {stats['count']}")  # Simplified
        
        return "\n".join(lines)
    
    @staticmethod
    def to_json_format() -> Dict[str, Any]:
        """Export metrics in JSON format"""
        return metrics.get_metrics()


# Default alert handlers
async def log_alert_handler(alert: Dict[str, Any]):
    """Log alert to structured logger"""
    logger.warning("Health alert", **alert)


async def console_alert_handler(alert: Dict[str, Any]):
    """Print alert to console"""
    print(f"ALERT [{alert['type'].upper()}] {alert['service']}: {alert['message']}")


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