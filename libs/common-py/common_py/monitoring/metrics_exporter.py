from typing import Dict, Any
from ..metrics import metrics

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
