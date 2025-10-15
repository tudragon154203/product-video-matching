"""
Standalone observability validation tests for collection phase integration.
Tests the observability infrastructure independently of the main collection workflow.
"""
import pytest
import asyncio
import json
import logging
from datetime import datetime
from unittest.mock import Mock, patch

from support.observability_validator import (
    LogCapture, LogValidator, MetricsCapture, MetricsValidator,
    HealthValidator, ObservabilityValidator
)
from common_py.logging_config import configure_logging, set_correlation_id
from common_py.metrics import metrics


class TestLogCapture:
    """Test log capture functionality"""
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_log_capture_start_stop(self, log_capture):
        """Test starting and stopping log capture"""
        # Capture should already be started by fixture
        assert len(log_capture.captured_logs) >= 0
        
        # Create a test logger and log a message
        test_logger = configure_logging("test-service:test-file")
        test_logger.info("Test message", correlation_id="test-123")
        
        # Stop capture
        log_capture.stop_capture()
        
        # Should have captured the test message
        assert len(log_capture.captured_logs) > 0
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_get_logs_by_correlation_id(self, log_capture):
        """Test filtering logs by correlation ID"""
        # Create test log entries
        log_capture.captured_logs = [
            {
                "raw": '{"message": "test1", "correlation_id": "test-123"}',
                "parsed": {"message": "test1", "correlation_id": "test-123"},
                "correlation_id": "test-123"
            },
            {
                "raw": '{"message": "test2", "correlation_id": "test-456"}',
                "parsed": {"message": "test2", "correlation_id": "test-456"},
                "correlation_id": "test-456"
            }
        ]
        
        # Filter by correlation ID
        filtered_logs = log_capture.get_logs_by_correlation_id("test-123")
        assert len(filtered_logs) == 1
        assert filtered_logs[0]["correlation_id"] == "test-123"
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_get_logs_by_service(self, log_capture):
        """Test filtering logs by service name"""
        # Create test log entries
        log_capture.captured_logs = [
            {
                "raw": '{"message": "test1"}',
                "parsed": {"message": "test1"},
                "logger_name": "main-api:endpoints"
            },
            {
                "raw": '{"message": "test2"}',
                "parsed": {"message": "test2"},
                "logger_name": "video-crawler:service"
            }
        ]
        
        # Filter by service
        filtered_logs = log_capture.get_logs_by_service("main-api")
        assert len(filtered_logs) == 1
        assert filtered_logs[0]["logger_name"] == "main-api:endpoints"
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_clear_logs(self, log_capture):
        """Test clearing captured logs"""
        # Add some test logs
        log_capture.captured_logs = [{"test": "log"}]
        
        # Clear logs
        log_capture.clear_logs()
        
        # Should be empty
        assert len(log_capture.captured_logs) == 0


class TestLogValidator:
    """Test log validation functionality"""
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_validate_logger_name_format(self):
        """Test logger name format validation"""
        # Valid names
        assert LogValidator.validate_logger_name_format("main-api:endpoints")
        assert LogValidator.validate_logger_name_format("video-crawler:service")
        assert LogValidator.validate_logger_name_format("common-py:messaging")
        assert LogValidator.validate_logger_name_format("scripts:migrations")
        
        # Invalid names
        assert not LogValidator.validate_logger_name_format("main.api.endpoints")
        assert not LogValidator.validate_logger_name_format("main_api:endpoints")
        assert not LogValidator.validate_logger_name_format("main-api:endpoints:extra")
        assert not LogValidator.validate_logger_name_format("Main-Api:Endpoints")
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_validate_standard_fields(self):
        """Test standard log field validation"""
        # Valid log entry
        valid_log = {
            "timestamp": "2023-01-01T12:00:00+07:00",
            "name": "main-api:endpoints",
            "level": "INFO",
            "message": "Test message"
        }
        assert LogValidator.validate_standard_fields(valid_log)
        
        # Missing fields
        invalid_log = {
            "timestamp": "2023-01-01T12:00:00+07:00",
            "name": "main-api:endpoints"
            # Missing level and message
        }
        assert not LogValidator.validate_standard_fields(invalid_log)
        
        # Invalid timestamp
        invalid_timestamp_log = {
            "timestamp": "invalid-timestamp",
            "name": "main-api:endpoints",
            "level": "INFO",
            "message": "Test message"
        }
        assert not LogValidator.validate_standard_fields(invalid_timestamp_log)
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_validate_correlation_id_presence(self):
        """Test correlation ID presence validation"""
        logs = [
            {
                "correlation_id": "test-123",
                "parsed": {"correlation_id": "test-123"}
            },
            {
                "correlation_id": "test-456",
                "parsed": {"correlation_id": "test-456"}
            }
        ]
        
        # Should find correlation ID
        assert LogValidator.validate_correlation_id_presence(logs, "test-123")
        
        # Should not find correlation ID
        assert not LogValidator.validate_correlation_id_presence(logs, "nonexistent")
        
        # Empty logs
        assert not LogValidator.validate_correlation_id_presence([], "test-123")
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_validate_service_logs(self):
        """Test service log validation"""
        logs = [
            {
                "logger_name": "main-api:endpoints",
                "parsed": {"message": "test"}
            },
            {
                "logger_name": "video-crawler:service",
                "parsed": {"message": "test"}
            },
            {
                "logger_name": "invalid.logger.name",
                "parsed": {"message": "test"}
            }
        ]
        
        expected_services = ["main-api", "video-crawler"]
        results = LogValidator.validate_service_logs(logs, expected_services)
        
        # Should validate main-api and video-crawler
        assert results["main-api"] == True
        assert results["video-crawler"] == True


class TestMetricsCapture:
    """Test metrics capture functionality"""
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_metrics_capture_start_stop(self):
        """Test starting and stopping metrics capture"""
        capture = MetricsCapture()
        
        # Start capture
        capture.start_capture()
        assert capture.start_snapshot is not None
        
        # Increment some metrics
        metrics.increment_counter("events_total", tags={"event": "test_event"})
        
        # Stop capture
        capture.stop_capture()
        assert capture.end_snapshot is not None
        
        # Should capture the increment
        increment = capture.get_counter_increment("events_total[event=test_event]")
        assert increment >= 0
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_get_events_total_counter(self):
        """Test getting events_total counter"""
        capture = MetricsCapture()
        
        # Mock snapshots
        capture.start_snapshot = {
            "counters": {
                "events_total[event=test_event]": 5,
                "other_counter": 10
            }
        }
        
        capture.end_snapshot = {
            "counters": {
                "events_total[event=test_event]": 8,
                "other_counter": 12
            }
        }
        
        # Should get the increment
        increment = capture.get_events_total_counter("test_event")
        assert increment == 3
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_get_all_counter_increments(self):
        """Test getting all counter increments"""
        capture = MetricsCapture()
        
        # Mock snapshots
        capture.start_snapshot = {
            "counters": {
                "counter1": 5,
                "counter2": 10
            }
        }
        
        capture.end_snapshot = {
            "counters": {
                "counter1": 8,
                "counter2": 15,
                "counter3": 20
            }
        }
        
        # Should get all increments
        increments = capture.get_all_counter_increments()
        assert increments["counter1"] == 3
        assert increments["counter2"] == 5
        assert increments["counter3"] == 20


class TestMetricsValidator:
    """Test metrics validation functionality"""
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_validate_events_total_counter(self):
        """Test events_total counter validation"""
        capture = MetricsCapture()
        
        # Mock successful capture
        with patch.object(capture, 'get_events_total_counter', return_value=5):
            assert MetricsValidator.validate_events_total_counter(capture, "test_event")
            assert MetricsValidator.validate_events_total_counter(capture, "test_event", expected_minimum=3)
            assert not MetricsValidator.validate_events_total_counter(capture, "test_event", expected_minimum=10)
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_validate_collection_metrics(self):
        """Test collection metrics validation"""
        capture = MetricsCapture()
        
        # Mock successful validation
        with patch.object(MetricsValidator, 'validate_events_total_counter', return_value=True):
            results = MetricsValidator.validate_collection_metrics(capture)
            assert results["products_collections_completed"]
            assert results["videos_collections_completed"]
        
        # Mock failed validation
        with patch.object(MetricsValidator, 'validate_events_total_counter', return_value=False):
            results = MetricsValidator.validate_collection_metrics(capture)
            assert not results["products_collections_completed"]
            assert not results["videos_collections_completed"]


class TestHealthValidator:
    """Test health validation functionality"""
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_health_validator_initialization(self, db_manager, message_broker):
        """Test health validator initialization"""
        validator = HealthValidator(db_manager, message_broker)
        
        # Should have standard health checks
        assert "database" in validator.health_checker.checks
        assert "message_broker" in validator.health_checker.checks
        assert "dlq" in validator.health_checker.checks
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_validate_health_status(self, db_manager, message_broker):
        """Test health status validation"""
        validator = HealthValidator(db_manager, message_broker)
        
        # Mock health checks
        with patch.object(validator, '_check_database', return_value=True), \
             patch.object(validator, '_check_message_broker', return_value=True), \
             patch.object(validator, '_check_dlq', return_value={"healthy": True}):
            
            status = await validator.validate_health_status()
            
            assert status["service"] == "test-observability"
            assert "status" in status
            assert "checks" in status
            assert "timestamp" in status
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_assert_healthy_success(self, db_manager, message_broker):
        """Test successful health assertion"""
        validator = HealthValidator(db_manager, message_broker)
        
        # Mock healthy status
        mock_status = {
            "status": "healthy",
            "checks": {
                "database": {"status": "healthy"},
                "message_broker": {"status": "healthy"},
                "dlq": {"status": "healthy"}
            }
        }
        
        with patch.object(validator, 'validate_health_status', return_value=mock_status):
            result = await validator.assert_healthy()
            assert result["status"] == "healthy"
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_assert_healthy_failure(self, db_manager, message_broker):
        """Test failed health assertion"""
        validator = HealthValidator(db_manager, message_broker)
        
        # Mock unhealthy status
        mock_status = {
            "status": "unhealthy",
            "checks": {
                "database": {"status": "unhealthy"},
                "message_broker": {"status": "healthy"},
                "dlq": {"status": "healthy"}
            }
        }
        
        with patch.object(validator, 'validate_health_status', return_value=mock_status):
            with pytest.raises(AssertionError):
                await validator.assert_healthy()


class TestObservabilityValidator:
    """Test main observability validator functionality"""
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_observability_validator_initialization(self, db_manager, message_broker):
        """Test observability validator initialization"""
        validator = ObservabilityValidator(db_manager, message_broker)
        
        # Should have all components
        assert validator.log_capture is not None
        assert validator.log_validator is not None
        assert validator.metrics_capture is not None
        assert validator.metrics_validator is not None
        assert validator.health_validator is not None
        assert not validator.is_capturing
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_start_stop_observability_capture(self, observability_validator):
        """Test starting and stopping observability capture"""
        validator = observability_validator
        
        # Start capture
        validator.start_observability_capture()
        assert validator.is_capturing
        
        # Stop capture
        validator.stop_observability_capture()
        assert not validator.is_capturing
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_validate_collection_phase_observability(self, observability_validator):
        """Test comprehensive observability validation"""
        validator = observability_validator
        
        # Mock successful validation
        with patch.object(validator.log_validator, 'validate_correlation_id_presence', return_value=True), \
             patch.object(validator.log_validator, 'validate_service_logs', return_value={"main-api": True}), \
             patch.object(validator.metrics_validator, 'validate_collection_metrics', return_value={"products_collections_completed": True, "videos_collections_completed": True}), \
             patch.object(validator.health_validator, 'validate_health_status', return_value={"status": "healthy", "checks": {}}):
            
            results = await validator.validate_collection_phase_observability("test-123")
            
            assert results["correlation_id"] == "test-123"
            assert results["overall_valid"]
            assert "logs" in results
            assert "metrics" in results
            assert "health" in results
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_assert_observability_requirements_success(self, observability_validator):
        """Test successful observability requirements assertion"""
        validator = observability_validator
        
        # Mock successful validation
        mock_results = {
            "overall_valid": True,
            "logs": {"correlation_present": True, "services": {"main-api": True}},
            "metrics": {"products_collections_completed": True, "videos_collections_completed": True},
            "health": {"status": "healthy", "checks": {"dlq": {"status": "healthy"}}}
        }
        
        with patch.object(validator, 'validate_collection_phase_observability', return_value=mock_results):
            result = await validator.assert_observability_requirements("test-123")
            assert result["overall_valid"]
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_assert_observability_requirements_failure(self, observability_validator):
        """Test failed observability requirements assertion"""
        validator = observability_validator
        
        # Mock failed validation
        mock_results = {
            "overall_valid": False,
            "logs": {"correlation_present": False, "services": {"main-api": True}},
            "metrics": {"products_collections_completed": False, "videos_collections_completed": True},
            "health": {"status": "unhealthy", "checks": {"dlq": {"status": "unhealthy"}}}
        }
        
        with patch.object(validator, 'validate_collection_phase_observability', return_value=mock_results):
            with pytest.raises(AssertionError):
                await validator.assert_observability_requirements("test-123")
    
    @pytest.mark.observability
    @pytest.mark.integration
    def test_clear_all_captures(self, observability_validator):
        """Test clearing all captures"""
        validator = observability_validator
        
        # Add some test data
        validator.log_capture.captured_logs = [{"test": "log"}]
        validator.metrics_capture = MetricsCapture()
        
        # Clear all
        validator.clear_all_captures()
        
        # Should be empty
        assert len(validator.log_capture.captured_logs) == 0


class TestObservabilityIntegration:
    """Integration tests for observability validation"""
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_full_observability_workflow(self, collection_phase_with_observability):
        """
        Test the full observability workflow with collection phase.
        This test demonstrates the complete observability validation in action.
        """
        env = collection_phase_with_observability
        obs_validator = env["observability"]
        job_id = env["job_id"]
        
        # Create a test logger and generate some logs
        test_logger = configure_logging("test-service:observability")
        
        # Set correlation ID and log some messages
        set_correlation_id(f"test-{job_id}")
        test_logger.info("Starting collection phase", job_id=job_id)
        test_logger.info("Processing products", job_id=job_id)
        test_logger.info("Processing videos", job_id=job_id)
        test_logger.info("Collection phase complete", job_id=job_id)
        
        # Increment some test metrics
        metrics.increment_counter("events_total", tags={"event": "products_collections_completed"})
        metrics.increment_counter("events_total", tags={"event": "videos_collections_completed"})
        
        # Validate observability
        results = await obs_validator.validate_collection_phase_observability(
            correlation_id=f"test-{job_id}",
            expected_services=["test-service"]
        )
        
        # Verify results structure
        assert "correlation_id" in results
        assert "validation_timestamp" in results
        assert "logs" in results
        assert "metrics" in results
        assert "health" in results
        assert "overall_valid" in results
        
        # Should have captured logs with correlation ID
        assert results["logs"]["correlation_logs_count"] > 0
        assert results["logs"]["correlation_present"]
        
        # Should have service logs
        assert "test-service" in results["logs"]["services"]
        
        # Should have health status
        assert "status" in results["health"]
        
        # Clear correlation ID
        set_correlation_id(None)
    
    @pytest.mark.asyncio
    @pytest.mark.observability
    @pytest.mark.integration
    async def test_observability_with_mock_services(self, observability_validator):
        """Test observability validation with mock service logs"""
        validator = observability_validator
        
        # Start capture
        validator.start_observability_capture()
        
        # Generate mock logs from different services
        services = [
            ("main-api:endpoints", "API request received"),
            ("video-crawler:service", "Video crawl started"),
            ("vision-embedding:processor", "Embedding generated"),
            ("vision-keypoint:extractor", "Keypoints extracted"),
            ("matcher:service", "Matching completed")
        ]
        
        correlation_id = "test-integration-123"
        set_correlation_id(correlation_id)
        
        for service_name, message in services:
            test_logger = configure_logging(service_name)
            test_logger.info(message, job_id="test-job-123")
        
        # Generate metrics
        metrics.increment_counter("events_total", tags={"event": "products_collections_completed"})
        metrics.increment_counter("events_total", tags={"event": "videos_collections_completed"})
        
        # Stop capture
        validator.stop_observability_capture()
        
        # Validate observability
        results = await validator.validate_collection_phase_observability(
            correlation_id=correlation_id,
            expected_services=["main-api", "video-crawler", "vision-embedding", "vision-keypoint", "matcher"]
        )
        
        # Verify all services logged
        assert all(results["logs"]["services"].values())
        
        # Verify metrics were captured
        assert results["metrics"]["products_collections_completed"]
        assert results["metrics"]["videos_collections_completed"]
        
        # Clear correlation ID
        set_correlation_id(None)
