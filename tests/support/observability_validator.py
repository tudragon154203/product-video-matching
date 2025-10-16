"""
Observability validation utilities for collection phase integration tests.
Provides comprehensive validation of logs, metrics, and health checks.
"""
import asyncio
import json
import re
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import os

from common_py.logging_config import configure_logging
from common_py.metrics import metrics, MetricsCollector
from common_py.health import HealthChecker, check_database_connection, check_message_broker_connection

logger = configure_logging("test-utils:observability-validator")


class LogCapture:
    """
    Captures and validates log messages during integration tests.
    """
    
    def __init__(self):
        self.captured_logs = []
        self.log_handlers = []
        self.original_handlers = {}
        
    def start_capture(self):
        """Start capturing log messages"""
        import logging
        
        # Store original handlers
        root_logger = logging.getLogger()
        self.original_handlers = {
            name: logger.handlers[:] 
            for name, logger in logging.Logger.manager.loggerDict.items() 
            if hasattr(logger, 'handlers')
        }
        
        # Create custom handler for capture
        class TestLogHandler(logging.Handler):
            def __init__(self, capture_instance):
                super().__init__()
                self.capture = capture_instance
                
            def emit(self, record):
                try:
                    log_entry = self.format(record)
                    
                    # Parse JSON logs if possible
                    try:
                        parsed_log = json.loads(log_entry)
                        self.capture.captured_logs.append({
                            "raw": log_entry,
                            "parsed": parsed_log,
                            "timestamp": datetime.fromtimestamp(record.created),
                            "level": record.levelname,
                            "logger_name": record.name,
                            "correlation_id": getattr(record, 'correlation_id', None)
                        })
                    except (json.JSONDecodeError, TypeError):
                        # Handle non-JSON logs
                        self.capture.captured_logs.append({
                            "raw": log_entry,
                            "parsed": None,
                            "timestamp": datetime.fromtimestamp(record.created),
                            "level": record.levelname,
                            "logger_name": record.name,
                            "correlation_id": getattr(record, 'correlation_id', None)
                        })
                except Exception:
                    pass  # Ignore logging errors during capture
        
        # Add capture handler to root logger
        self.test_handler = TestLogHandler(self)
        self.test_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(self.test_handler)
        
        logger.info("Started log capture")
    
    def stop_capture(self):
        """Stop capturing log messages and restore original handlers"""
        import logging
        
        # Remove test handler
        root_logger = logging.getLogger()
        if hasattr(self, 'test_handler'):
            root_logger.removeHandler(self.test_handler)
        
        logger.info("Stopped log capture", captured_count=len(self.captured_logs))
    
    def get_logs_by_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get logs filtered by correlation ID"""
        return [
            log for log in self.captured_logs 
            if log.get("correlation_id") == correlation_id or
               (log.get("parsed") and log["parsed"].get("correlation_id") == correlation_id)
        ]
    
    def get_logs_by_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Get logs filtered by service name"""
        return [
            log for log in self.captured_logs 
            if log.get("logger_name", "").startswith(service_name)
        ]
    
    def clear_logs(self):
        """Clear captured logs"""
        self.captured_logs.clear()
        logger.info("Cleared captured logs")


class LogValidator:
    """
    Validates log messages according to sprint_11_unified_logging_standards.md
    """
    
    @staticmethod
    def validate_logger_name_format(logger_name: str) -> bool:
        """
        Validate logger name follows `microservice:file` format.
        
        Args:
            logger_name: Logger name to validate
            
        Returns:
            True if format is correct
        """
        # Pattern: [a-z0-9-]+:[a-z0-9_]+
        pattern = r'^[a-z0-9-]+:[a-z0-9_]+$'
        return bool(re.match(pattern, logger_name))
    
    @staticmethod
    def validate_standard_fields(log_entry: Dict[str, Any]) -> bool:
        """
        Validate that log entry contains standard fields.
        
        Args:
            log_entry: Parsed log entry
            
        Returns:
            True if all standard fields are present
        """
        required_fields = ["timestamp", "name", "level", "message"]
        
        for field in required_fields:
            if field not in log_entry:
                return False
        
        # Validate timestamp format
        try:
            if isinstance(log_entry["timestamp"], str):
                # Try ISO format
                datetime.fromisoformat(log_entry["timestamp"])
            else:
                # Should be datetime object
                if not isinstance(log_entry["timestamp"], datetime):
                    return False
        except (ValueError, TypeError):
            return False
        
        return True
    
    @staticmethod
    def validate_correlation_id_presence(
        logs: List[Dict[str, Any]], 
        correlation_id: str,
        require_all: bool = False
    ) -> bool:
        """
        Validate correlation ID presence in logs.
        
        Args:
            logs: List of log entries
            correlation_id: Expected correlation ID
            require_all: If True, all logs must have correlation_id
            
        Returns:
            True if validation passes
        """
        if not logs:
            return False
        
        logs_with_correlation = 0
        
        for log in logs:
            log_correlation_id = (
                log.get("correlation_id") or 
                (log.get("parsed") and log["parsed"].get("correlation_id"))
            )
            
            if log_correlation_id == correlation_id:
                logs_with_correlation += 1
            elif require_all and log_correlation_id is None:
                return False
        
        # At least some logs should have the correlation ID
        return logs_with_correlation > 0
    
    @staticmethod
    def validate_service_logs(
        logs: List[Dict[str, Any]], 
        expected_services: List[str]
    ) -> Dict[str, bool]:
        """
        Validate that expected services have logged properly.
        
        Args:
            logs: List of log entries
            expected_services: List of expected service names
            
        Returns:
            Dictionary mapping service names to validation results
        """
        results = {}
        
        for service in expected_services:
            service_logs = [
                log for log in logs 
                if log.get("logger_name", "").startswith(service)
            ]
            
            # Check if service has logs and they follow standards
            results[service] = len(service_logs) > 0 and all(
                LogValidator.validate_logger_name_format(log.get("logger_name", ""))
                for log in service_logs
            )
        
        return results


class MetricsCapture:
    """
    Captures and validates metrics during integration tests.
    """
    
    def __init__(self):
        self.original_metrics = None
        self.captured_metrics = MetricsCollector()
        self.start_snapshot = None
        self.end_snapshot = None
        
    def start_capture(self):
        """Start capturing metrics"""
        # Take initial snapshot
        self.start_snapshot = metrics.get_metrics()
        logger.info("Started metrics capture", start_snapshot=self.start_snapshot)
    
    def stop_capture(self):
        """Stop capturing metrics and take final snapshot"""
        # Take final snapshot
        self.end_snapshot = metrics.get_metrics()
        logger.info("Stopped metrics capture", end_snapshot=self.end_snapshot)
    
    def get_counter_increment(self, counter_name: str) -> int:
        """
        Get the increment value for a specific counter.
        
        Args:
            counter_name: Name of the counter
            
        Returns:
            Increment value (end - start)
        """
        if not self.start_snapshot or not self.end_snapshot:
            return 0
        
        start_value = self.start_snapshot.get("counters", {}).get(counter_name, 0)
        end_value = self.end_snapshot.get("counters", {}).get(counter_name, 0)
        
        return end_value - start_value
    
    def get_events_total_counter(self, event_name: str) -> int:
        """
        Get the events_total counter for a specific event.
        
        Args:
            event_name: Name of the event
            
        Returns:
            Counter value
        """
        counter_key = f"events_total[event={event_name}]"
        return self.get_counter_increment(counter_key)
    
    def get_all_counter_increments(self) -> Dict[str, int]:
        """Get all counter increments"""
        if not self.start_snapshot or not self.end_snapshot:
            return {}
        
        increments = {}
        all_counters = set(self.start_snapshot.get("counters", {}).keys()) | \
                      set(self.end_snapshot.get("counters", {}).keys())
        
        for counter in all_counters:
            increments[counter] = self.get_counter_increment(counter)
        
        return increments


class MetricsValidator:
    """
    Validates metrics according to observability requirements.
    """
    
    @staticmethod
    def validate_events_total_counter(
        metrics_capture: MetricsCapture,
        event_name: str,
        expected_minimum: int = 1
    ) -> bool:
        """
        Validate events_total counter for a specific event.
        
        Args:
            metrics_capture: Metrics capture instance
            event_name: Event name to validate
            expected_minimum: Minimum expected count
            
        Returns:
            True if validation passes
        """
        count = metrics_capture.get_events_total_counter(event_name)
        return count >= expected_minimum
    
    @staticmethod
    def validate_collection_metrics(
        metrics_capture: MetricsCapture
    ) -> Dict[str, bool]:
        """
        Validate collection phase specific metrics.
        
        Args:
            metrics_capture: Metrics capture instance
            
        Returns:
            Dictionary of validation results
        """
        results = {}
        
        # Validate products_collections_completed
        results["products_collections_completed"] = MetricsValidator.validate_events_total_counter(
            metrics_capture, "products_collections_completed"
        )
        
        # Validate videos_collections_completed
        results["videos_collections_completed"] = MetricsValidator.validate_events_total_counter(
            metrics_capture, "videos_collections_completed"
        )
        
        return results


class HealthValidator:
    """
    Validates health check endpoints and service health.
    """
    
    def __init__(self, db_manager, message_broker):
        self.db_manager = db_manager
        self.message_broker = message_broker
        self.health_checker = HealthChecker("test-observability")
        
        # Add standard health checks
        self.health_checker.add_check("database", self._check_database)
        self.health_checker.add_check("message_broker", self._check_message_broker)
        self.health_checker.add_check("dlq", self._check_dlq)
    
    async def _check_database(self) -> bool:
        """Check database connection"""
        return await check_database_connection(self.db_manager)
    
    async def _check_message_broker(self) -> bool:
        """Check message broker connection"""
        return await check_message_broker_connection(self.message_broker)
    
    async def _check_dlq(self) -> Dict[str, Any]:
        """Check DLQ is empty"""
        try:
            # Check for messages in DLQ
            dlq_count = await self.message_broker.get_queue_message_count("dlq")
            return {
                "healthy": dlq_count == 0,
                "dlq_count": dlq_count,
                "message": "DLQ is empty" if dlq_count == 0 else f"DLQ has {dlq_count} messages"
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "message": f"Failed to check DLQ: {str(e)}"
            }
    
    async def validate_health_status(self) -> Dict[str, Any]:
        """
        Validate overall health status.
        
        Returns:
            Health status with detailed results
        """
        return await self.health_checker.get_health_status()
    
    async def assert_healthy(self) -> Dict[str, Any]:
        """
        Assert that all health checks pass.
        
        Returns:
            Health status if all checks pass
            
        Raises:
            AssertionError: If any health check fails
        """
        status = await self.validate_health_status()
        
        if status["status"] != "healthy":
            failed_checks = [
                name for name, check in status["checks"].items()
                if check["status"] != "healthy"
            ]
            
            raise AssertionError(
                f"Health checks failed: {failed_checks}. "
                f"Status: {status}"
            )
        
        return status


class ObservabilityValidator:
    """
    Main observability validator that combines log, metrics, and health validation.
    """
    
    def __init__(self, db_manager, message_broker):
        self.log_capture = LogCapture()
        self.log_validator = LogValidator()
        self.metrics_capture = MetricsCapture()
        self.metrics_validator = MetricsValidator()
        self.health_validator = HealthValidator(db_manager, message_broker)
        
        self.is_capturing = False
    
    def start_observability_capture(self):
        """Start capturing all observability data"""
        if self.is_capturing:
            logger.warning("Observability capture already started")
            return
        
        self.log_capture.start_capture()
        self.metrics_capture.start_capture()
        self.is_capturing = True
        
        logger.info("Started observability capture")
    
    def stop_observability_capture(self):
        """Stop capturing all observability data"""
        if not self.is_capturing:
            logger.warning("Observability capture not started")
            return
        
        self.log_capture.stop_capture()
        self.metrics_capture.stop_capture()
        self.is_capturing = False
        
        logger.info("Stopped observability capture")
    
    async def validate_collection_phase_observability(
        self,
        correlation_id: str,
        expected_services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of collection phase observability.
        
        Args:
            correlation_id: Correlation ID to validate
            expected_services: List of expected service names
            
        Returns:
            Comprehensive validation results
        """
        if expected_services is None:
            expected_services = [
                "main-api",
                "video-crawler", 
                "vision-embedding",
                "vision-keypoint",
                "matcher"
            ]
        
        results = {
            "correlation_id": correlation_id,
            "validation_timestamp": datetime.utcnow().isoformat(),
            "logs": {},
            "metrics": {},
            "health": {}
        }
        
        # Validate logs
        correlation_logs = self.log_capture.get_logs_by_correlation_id(correlation_id)
        results["logs"]["correlation_logs_count"] = len(correlation_logs)
        results["logs"]["correlation_present"] = self.log_validator.validate_correlation_id_presence(
            correlation_logs, correlation_id
        )
        
        # Validate service logs
        service_results = self.log_validator.validate_service_logs(
            self.log_capture.captured_logs, expected_services
        )
        results["logs"]["services"] = service_results
        
        # Validate metrics
        metrics_results = self.metrics_validator.validate_collection_metrics(
            self.metrics_capture
        )
        results["metrics"] = metrics_results
        
        # Validate health
        health_status = await self.health_validator.validate_health_status()
        results["health"] = health_status

        # Overall validation result
        results["overall_valid"] = (
            results["logs"]["correlation_present"] and
            all(results["logs"]["services"].values()) and
            all(results["metrics"].values()) and
            results["health"]["status"] == "healthy"
        )

        return results
    
    async def assert_observability_requirements(
        self,
        correlation_id: str,
        expected_services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Assert that all observability requirements are met.
        
        Args:
            correlation_id: Correlation ID to validate
            expected_services: List of expected service names
            
        Returns:
            Validation results if all requirements pass
            
        Raises:
            AssertionError: If any requirement fails
        """
        results = await self.validate_collection_phase_observability(
            correlation_id, expected_services
        )
        
        # Check overall validation
        if not results["overall_valid"]:
            errors = []
            
            # Log errors
            if not results["logs"]["correlation_present"]:
                errors.append("Correlation ID not found in logs")
            
            failed_services = [
                service for service, valid in results["logs"]["services"].items()
                if not valid
            ]
            if failed_services:
                errors.append(f"Service logs validation failed: {failed_services}")
            
            # Metrics errors
            failed_metrics = [
                metric for metric, valid in results["metrics"].items()
                if not valid
            ]
            if failed_metrics:
                errors.append(f"Metrics validation failed: {failed_metrics}")
            
            # Health errors
            if results["health"]["status"] != "healthy":
                errors.append(f"Health check failed: {results['health']['status']}")
            
            raise AssertionError(
                f"Observability requirements not met: {'; '.join(errors)}. "
                f"Results: {results}"
            )
        
        return results
    
    def clear_all_captures(self):
        """Clear all captured observability data"""
        self.log_capture.clear_logs()
        self.metrics_capture = MetricsCapture()
        logger.info("Cleared all observability captures")