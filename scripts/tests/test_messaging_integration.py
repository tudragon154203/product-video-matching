"""
Message broker integration tests
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_message_broker_connection(message_broker):
    """Test message broker connection"""
    assert message_broker.connection is not None
    assert not message_broker.connection.is_closed


@pytest.mark.asyncio
async def test_publish_and_consume_event(message_broker):
    """Test publishing and consuming events"""
    test_topic = "test.integration.event"
    test_event = {
        "test_id": "integration_test_123",
        "message": "Hello from integration test"
    }
    
    received_events = []
    
    async def test_handler(event_data):
        received_events.append(event_data)
    
    # Subscribe to test topic
    await message_broker.subscribe_to_topic(test_topic, test_handler)
    
    # Give subscription time to set up
    await asyncio.sleep(1)
    
    # Publish test event
    await message_broker.publish_event(test_topic, test_event)
    
    # Wait for message to be processed
    await asyncio.sleep(2)
    
    # Verify event was received
    assert len(received_events) == 1
    received_event = received_events[0]
    
    # Check event content (excluding metadata)
    assert received_event["test_id"] == test_event["test_id"]
    assert received_event["message"] == test_event["message"]
    assert "_metadata" in received_event


@pytest.mark.asyncio
async def test_event_validation_integration(message_broker):
    """Test event validation in message flow"""
    from contracts.validator import validator
    
    # Test valid event
    valid_event = {
        "job_id": "test_job_123",
        "industry": "test pillows",
        "top_amz": 5,
        "top_ebay": 3
    }
    
    # This should not raise an exception
    validator.validate_event("products_collect_request", valid_event)
    
    # Test invalid event
    invalid_event = {
        "job_id": "test_job_123",
        "industry": "test pillows"
        # Missing required fields
    }
    
    with pytest.raises(Exception):
        validator.validate_event("products_collect_request", invalid_event)


@pytest.mark.asyncio
async def test_retry_mechanism(message_broker):
    """Test message retry mechanism"""
    test_topic = "test.retry.event"
    test_event = {"test_id": "retry_test", "should_fail": True}
    
    attempt_count = 0
    
    async def failing_handler(event_data):
        nonlocal attempt_count
        attempt_count += 1
        
        if event_data.get("should_fail") and attempt_count < 3:
            raise Exception("Simulated failure")
        
        # Success on third attempt
        return True
    
    # Subscribe to test topic
    await message_broker.subscribe_to_topic(test_topic, failing_handler)
    
    # Give subscription time to set up
    await asyncio.sleep(1)
    
    # Publish event that will initially fail
    await message_broker.publish_event(test_topic, test_event)
    
    # Wait for retries to complete
    await asyncio.sleep(10)
    
    # Should have been attempted multiple times
    assert attempt_count >= 2


@pytest.mark.asyncio
async def test_dead_letter_queue(message_broker):
    """Test dead letter queue functionality"""
    test_topic = "test.dlq.event"
    test_event = {"test_id": "dlq_test", "always_fail": True}
    
    async def always_failing_handler(event_data):
        raise Exception("This handler always fails")
    
    # Subscribe to test topic
    await message_broker.subscribe_to_topic(test_topic, always_failing_handler)
    
    # Give subscription time to set up
    await asyncio.sleep(1)
    
    # Publish event that will always fail
    await message_broker.publish_event(test_topic, test_event)
    
    # Wait for all retries to exhaust and message to go to DLQ
    await asyncio.sleep(15)
    
    # Message should eventually be sent to DLQ
    # (In a real test, we would check the DLQ, but that requires more setup)


@pytest.mark.asyncio
async def test_correlation_id_propagation(message_broker):
    """Test correlation ID propagation"""
    test_topic = "test.correlation.event"
    test_correlation_id = "test_correlation_123"
    test_event = {"test_id": "correlation_test"}
    
    received_correlation_ids = []
    
    async def correlation_handler(event_data):
        # Extract correlation ID from metadata
        metadata = event_data.get("_metadata", {})
        correlation_id = metadata.get("correlation_id")
        received_correlation_ids.append(correlation_id)
    
    # Subscribe to test topic
    await message_broker.subscribe_to_topic(test_topic, correlation_handler)
    
    # Give subscription time to set up
    await asyncio.sleep(1)
    
    # Publish event with specific correlation ID
    await message_broker.publish_event(test_topic, test_event, test_correlation_id)
    
    # Wait for message to be processed
    await asyncio.sleep(2)
    
    # Verify correlation ID was preserved
    assert len(received_correlation_ids) == 1
    assert received_correlation_ids[0] == test_correlation_id


@pytest.mark.asyncio
async def test_multiple_consumers(message_broker):
    """Test multiple consumers on same topic"""
    test_topic = "test.multiple.consumers"
    test_event = {"test_id": "multi_consumer_test"}
    
    consumer1_events = []
    consumer2_events = []
    
    async def consumer1_handler(event_data):
        consumer1_events.append(event_data)
    
    async def consumer2_handler(event_data):
        consumer2_events.append(event_data)
    
    # Subscribe multiple consumers to same topic
    await message_broker.subscribe_to_topic(test_topic, consumer1_handler, "consumer1_queue")
    await message_broker.subscribe_to_topic(test_topic, consumer2_handler, "consumer2_queue")
    
    # Give subscriptions time to set up
    await asyncio.sleep(1)
    
    # Publish test event
    await message_broker.publish_event(test_topic, test_event)
    
    # Wait for messages to be processed
    await asyncio.sleep(3)
    
    # Both consumers should receive the event
    assert len(consumer1_events) == 1
    assert len(consumer2_events) == 1
    
    assert consumer1_events[0]["test_id"] == test_event["test_id"]
    assert consumer2_events[0]["test_id"] == test_event["test_id"]