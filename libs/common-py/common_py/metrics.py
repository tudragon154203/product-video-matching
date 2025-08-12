"""
Basic metrics collection utilities
"""
import time
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import structlog

logger = structlog.get_logger()


class MetricsCollector:
    """Simple in-memory metrics collector"""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(lambda: deque(maxlen=1000))  # Keep last 1000 values
        self.timers = {}
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        key = self._make_key(name, tags)
        self.counters[key] += value
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        key = self._make_key(name, tags)
        self.gauges[key] = value
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram value"""
        key = self._make_key(name, tags)
        self.histograms[key].append(value)
    
    def start_timer(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Start a timer and return timer ID"""
        key = self._make_key(name, tags)
        timer_id = f"{key}_{time.time()}"
        self.timers[timer_id] = {"key": key, "start_time": time.time()}
        return timer_id
    
    def stop_timer(self, timer_id: str):
        """Stop a timer and record the duration"""
        if timer_id in self.timers:
            timer_info = self.timers.pop(timer_id)
            duration = time.time() - timer_info["start_time"]
            self.record_histogram(timer_info["key"], duration)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        metrics = {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {}
        }
        
        # Calculate histogram statistics
        for key, values in self.histograms.items():
            if values:
                values_list = list(values)
                metrics["histograms"][key] = {
                    "count": len(values_list),
                    "min": min(values_list),
                    "max": max(values_list),
                    "avg": sum(values_list) / len(values_list),
                    "p50": self._percentile(values_list, 0.5),
                    "p95": self._percentile(values_list, 0.95),
                    "p99": self._percentile(values_list, 0.99)
                }
        
        return metrics
    
    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Create metric key with tags"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def _percentile(self, values: list, percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(percentile * (len(sorted_values) - 1))
        return sorted_values[index]


# Global metrics instance
metrics = MetricsCollector()


class TimerContext:
    """Context manager for timing operations"""
    
    def __init__(self, name: str, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.tags = tags
        self.timer_id = None
    
    def __enter__(self):
        self.timer_id = metrics.start_timer(self.name, self.tags)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timer_id:
            metrics.stop_timer(self.timer_id)


def timer(name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for timing function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TimerContext(name, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator


async def timer_async(name: str, tags: Optional[Dict[str, str]] = None):
    """Async decorator for timing function execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with TimerContext(name, tags):
                return await func(*args, **kwargs)
        return wrapper
    return decorator