# Vision Services Logging Standards

## Overview

This document defines standardized logging patterns for all vision services in the product-video-matching ecosystem. The goal is to ensure consistent, traceable, and structured logging across vision-embedding, vision-keypoint, and product-segmentor services.

## Core Principles

1. **Use `configure_logging` from common_py** - All services must use the centralized logging configuration
2. **Structured logging** - Always use keyword arguments instead of string formatting
3. **Consistent log levels** - Similar operations should use the same log levels across services
4. **Correlation ID tracking** - Include correlation IDs for request tracing
5. **Progress tracking** - Log batch processing and individual item processing consistently

## Standardized Log Templates

### 1. Service Initialization

```python
# In main.py
logger = configure_logging("vision-embedding")

# Service start
logger.info("Vision embedding service started")

# Service initialization
logger.info("Initializing vision embedding service", model_name=embed_model)

# Service shutdown
logger.info("Shutting down vision embedding service")
```

### 2. Batch Processing Start

```python
# Batch event received
logger.info("Batch event received", 
           job_id=job_id, 
           asset_type=asset_type,
           total_items=total_items,
           event_type=event_type)

# Batch processing started
logger.info("Starting batch processing", 
           job_id=job_id,
           asset_type=asset_type,
           total_items=total_items)

# Batch initialization completed
logger.info("Batch tracking initialized", 
           job_id=job_id,
           asset_type=asset_type,
           total_items=total_items)
```

### 3. Individual Item Processing

```python
# Item processing started
logger.info("Processing item", 
           job_id=job_id,
           asset_id=asset_id,
           asset_type=asset_type,
           item_path=item_path)

# Item processing completed successfully
logger.info("Item processed successfully", 
           job_id=job_id,
           asset_id=asset_id,
           asset_type=asset_type,
           processing_time_ms=processing_time)

# Item processing failed
logger.error("Item processing failed", 
            job_id=job_id,
            asset_id=asset_id,
            asset_type=asset_type,
            error=str(error),
            error_type=type(error).__name__)
```

### 4. Progress Tracking

```python
# Progress update
logger.debug("Progress update", 
            job_id=job_id,
            asset_type=asset_type,
            processed=processed_count,
            total=total_count,
            percentage=percentage)

# Progress milestone
logger.info("Progress milestone", 
           job_id=job_id,
           asset_type=asset_type,
           processed=processed_count,
           total=total_count,
           milestone="halfway" | "nearly_complete" | "complete")

# Batch completion
logger.info("Batch completed", 
           job_id=job_id,
           asset_type=asset_type,
           processed=processed_count,
           total=total_count,
            duration_ms=batch_duration)
```

### 5. Error Handling

```python
# General error with context
logger.error("Operation failed", 
            job_id=job_id,
            asset_id=asset_id,
            asset_type=asset_type,
            error=str(error),
            error_type=type(error).__name__,
            operation=operation_name)

# Validation error
logger.warning("Validation failed", 
              job_id=job_id,
              asset_id=asset_id,
              asset_type=asset_type,
              validation_field=field_name,
              validation_message=message)

# Resource not found
logger.warning("Resource not found", 
              job_id=job_id,
              asset_id=asset_id,
              asset_type=asset_type,
              resource_type=resource_name)
```

### 6. Event Publishing

```python
# Event published successfully
logger.info("Event published", 
           job_id=job_id,
           event_type=event_type,
           event_id=event_id,
           asset_type=asset_type,
           total_items=total_items,
           processed_items=processed_items)

# Completion event published
logger.info("Completion event published", 
           job_id=job_id,
           event_type=event_type,
           event_id=event_id,
           asset_type=asset_type,
           total_assets=total_assets,
           processed_assets=processed_assets,
           has_partial_completion=has_partial)
```

### 7. Asset Duplication Handling

```python
# Duplicate asset detected
logger.info("Skipping duplicate asset", 
           job_id=job_id,
           asset_id=asset_id,
           asset_type=asset_type)

# Duplicate batch event detected
logger.info("Ignoring duplicate batch event", 
           job_id=job_id,
           event_id=event_id,
           asset_type=asset_type)
```

### 8. Watermark/Timeout Handling

```python
# Watermark timer started
logger.debug("Watermark timer started", 
            job_id=job_id,
            ttl_seconds=ttl)

# Watermark timeout occurred
logger.warning("Watermark timeout occurred", 
              job_id=job_id,
              asset_type=asset_type,
              processed=processed_count,
              total=total_count)

# Immediate completion for zero assets
logger.info("Immediate completion for zero-asset job", 
           job_id=job_id,
           asset_type=asset_type)
```

## Service-Specific Templates

### Vision Embedding Service

```python
# Model initialization
logger.info("Initializing embedding extractor", model_name=embed_model)

# Embedding extraction
logger.debug("Extracting embeddings", 
            asset_id=asset_id,
            asset_type=asset_type,
            model_name=embed_model)

# Embedding extraction completed
logger.info("Embeddings extracted", 
           asset_id=asset_id,
           asset_type=asset_type,
            embedding_shape=embedding_shape)

# Database update
logger.debug("Database update completed", 
            asset_id=asset_id,
            asset_type=asset_type,
            operation="update_embeddings")
```

### Vision Keypoint Service

```python
# Keypoint extraction
logger.debug("Extracting keypoints", 
            asset_id=asset_id,
            asset_type=asset_type)

# Keypoint extraction completed
logger.info("Keypoints extracted", 
           asset_id=asset_id,
           asset_type=asset_type,
           keypoint_path=keypoint_path)

# Database update
logger.debug("Database update completed", 
            asset_id=asset_id,
            asset_type=asset_type,
            operation="update_keypoints")
```

### Product Segmentor Service

```python
# Model initialization
logger.info("Initializing segmentation model", 
           model_name=model_name,
           model_path=model_path)

# Segmentation processing
logger.debug("Processing segmentation", 
            asset_id=asset_id,
            asset_type=asset_type)

# Segmentation completed
logger.info("Segmentation completed", 
           asset_id=asset_id,
           asset_type=asset_type,
           mask_shape=mask_shape)

# Mask generation
logger.debug("Generating mask", 
            asset_id=asset_id,
            asset_type=asset_type)
```

## Log Level Guidelines

### DEBUG (Development Only)
- Detailed processing steps
- Resource initialization details
- Progress tracking updates
- Performance timing measurements

### INFO
- Service start/stop events
- Batch processing start/completion
- Individual item processing completion
- Event publishing
- Asset duplication handling
- Watermark timeout events

### WARNING
- Validation failures
- Resource not found scenarios
- Partial completions
- Performance thresholds exceeded

### ERROR
- Processing failures
- Database operation failures
- Event publishing failures
- Critical resource unavailability

### CRITICAL
- Service initialization failures
- Unrecoverable errors
- System-level failures

## Consistency Rules

### 1. Common Fields
All log messages should include consistent fields when applicable:

```python
# Required fields for job-related logs
{
    "job_id": str,           # Job identifier
    "asset_type": str,       # "image" or "video"
    "asset_id": str,         # Individual asset identifier
    "operation": str        # Specific operation being performed
}

# Required fields for batch logs
{
    "job_id": str,           # Job identifier
    "asset_type": str,       # "image" or "video"
    "total_items": int,      # Total items in batch
    "processed_items": int  # Items processed so far
}
```

### 2. Asset Type Consistency
- Use `"image"` for all image-related operations
- Use `"video"` for all video-related operations
- Use `"frame"` for video frame operations (when applicable)

### 3. Event Type Consistency
- Use standardized event names from contracts
- Include event_id in completion logs
- Use consistent naming for batch vs individual events

### 4. Error Handling Consistency
- Always include error type and message
- Include relevant context (job_id, asset_id, asset_type)
- Use appropriate log levels based on error severity

## Implementation Examples

### Handler Level Logging

```python
# In handlers/embedding_handler.py
from common_py.logging_config import configure_logging

logger = configure_logging("vision-embedding")

@validate_event("products_image_masked")
async def handle_products_image_masked(self, event_data):
    logger.info("Received product image masked event",
               job_id=event_data.get("job_id"),
               image_id=event_data.get("image_id"))
    
    try:
        await self.service.handle_products_image_masked(event_data)
        logger.info("Product image masked processing completed",
                   job_id=event_data.get("job_id"),
                   image_id=event_data.get("image_id"))
    except Exception as e:
        logger.error("Product image masked processing failed",
                    job_id=event_data.get("job_id"),
                    image_id=event_data.get("image_id"),
                    error=str(e))
        raise
```

### Service Level Logging

```python
# In services/service.py
from common_py.logging_config import configure_logging

logger = configure_logging("vision-embedding")

class VisionEmbeddingService:
    async def handle_products_image_masked(self, event_data):
        job_id = event_data["job_id"]
        image_id = event_data["image_id"]
        mask_path = event_data["mask_path"]
        
        logger.info("Processing masked product image",
                   job_id=job_id,
                   image_id=image_id,
                   mask_path=mask_path)
        
        try:
            # Process the image
            emb_rgb, emb_gray = await self.extractor.extract_embeddings_with_mask(local_path, mask_path)
            
            if emb_rgb is not None and emb_gray is not None:
                logger.info("Masked product image processed successfully",
                           job_id=job_id,
                           image_id=image_id)
            else:
                logger.error("Failed to extract embeddings from masked image",
                           job_id=job_id,
                           image_id=image_id)
                
        except Exception as e:
            logger.error("Masked product image processing failed",
                        job_id=job_id,
                        image_id=image_id,
                        error=str(e))
            raise
```

## Migration Guide

### Current Issues to Address

1. **Mixed logging approaches**: Some services use `structlog`, others use standard logging
2. **Inconsistent log levels**: Similar operations use different levels across services
3. **Missing structured data**: String formatting instead of keyword arguments
4. **Inconsistent field names**: Different naming conventions for similar data

### Migration Steps

1. **Replace all logger initialization** with `configure_logging`
2. **Update all log calls** to use structured format
3. **Standardize field names** across services
4. **Ensure consistent log levels** for similar operations
5. **Add missing context** to error logs
6. **Test the migration** with sample data

## Testing and Validation

### Automated Testing
- Log message format validation
- Required field presence checking
- Log level consistency verification
- Correlation ID propagation testing

### Manual Testing
- Visual inspection of log output
- Performance impact assessment
- Error scenario validation
- Cross-service log correlation

## Monitoring and Maintenance

### Log Analysis
- Use structured queries to filter and analyze logs
- Monitor error rates by service and operation type
- Track processing times and performance metrics
- Identify patterns in failure scenarios

### Continuous Improvement
- Regular review of log effectiveness
- Update templates based on operational needs
- Maintain consistency as services evolve
- Document any deviations from standards