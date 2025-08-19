import asyncio
from typing import Dict, Any, List, Callable
from ..logging_config import configure_logging
from ..metrics import metrics

logger = configure_logging("common-py")


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
