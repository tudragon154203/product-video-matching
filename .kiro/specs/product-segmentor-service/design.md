# Product Segmentor Service Design

## Overview

The Product Segmentor Service is a new microservice that will be inserted into the existing product-video matching pipeline between the collection phase and feature extraction phase. Its primary purpose is to generate product-focused masks for both catalog images and video keyframes, enabling downstream services to extract features only from product regions while ignoring people, backgrounds, and other distracting elements.

The service follows the established event-driven architecture pattern, consuming `*.ready` events and producing `*.masked` events that downstream services will process instead of the original raw images.

## Architecture

### Service Position in Pipeline

```
Collection Phase:
├── Dropship Product Finder → products.image.ready(.batch)
└── Video Crawler → video.keyframes.ready(.batch)
                    ↓
Product Segmentor Service:
├── Consumes: products.image.ready, products.images.ready.batch
├── Consumes: video.keyframes.ready, video.keyframes.ready.batch  
├── Produces: products.image.masked, products.images.masked.batch
└── Produces: video.keyframes.masked, video.keyframes.masked.batch
                    ↓
Feature Extraction Phase:
├── Vision Embedding (updated to consume *.masked events)
└── Vision Keypoint (updated to consume *.masked events)
```

### Event Flow Architecture

The service implements a dual-path processing model:

1. **Per-Asset Processing**: Processes individual images/frames and emits per-asset masked events
2. **Batch Completion Tracking**: Tracks completion of entire batches and emits batch completion events

### Segmentation Engine Architecture

The service uses a pluggable segmentation architecture to support different models:

```
SegmentationInterface (Abstract)
├── RMBGSegmentor (Remove Background)
├── YOLOSegmentor (Object Detection + Segmentation)
└── SAMSegmentor (Segment Anything Model)
```

## Components and Interfaces

### Core Components

#### 1. ProductSegmentorHandler
- **Purpose**: Event handling and orchestration
- **Responsibilities**:
  - Receive and validate incoming events
  - Coordinate with segmentation service
  - Emit outgoing masked events
  - Handle error scenarios and logging

#### 2. ProductSegmentorService  
- **Purpose**: Business logic and processing coordination
- **Responsibilities**:
  - Load and process images/frames
  - Coordinate with segmentation engine
  - Save masks to filesystem
  - Update database records
  - Track batch completion

#### 3. SegmentationEngine
- **Purpose**: Pluggable segmentation model interface
- **Responsibilities**:
  - Load configured segmentation model
  - Generate product masks from input images
  - Handle model-specific preprocessing/postprocessing
  - Provide consistent interface across different models

#### 4. FileManager
- **Purpose**: File system operations for masks
- **Responsibilities**:
  - Create mask directory structure
  - Save mask files with proper naming
  - Handle file I/O errors
  - Ensure atomic file operations

### Interface Definitions

#### SegmentationInterface
```python
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

class SegmentationInterface(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the segmentation model"""
        pass
    
    @abstractmethod
    async def segment_image(self, image_path: str) -> Optional[np.ndarray]:
        """Generate product mask for image
        
        Args:
            image_path: Path to input image
            
        Returns:
            Binary mask as numpy array or None if segmentation fails
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup model resources"""
        pass
```

#### Event Handler Interface
```python
class ProductSegmentorHandler:
    async def handle_products_images_ready(self, event_data: dict) -> None:
        """Process single product image ready event"""
        
    async def handle_products_images_ready_batch(self, event_data: dict) -> None:
        """Process product images batch completion event"""
        
    async def handle_video_keyframes_ready(self, event_data: dict) -> None:
        """Process video keyframes ready event"""
        
    async def handle_video_keyframes_ready_batch(self, event_data: dict) -> None:
        """Process video keyframes batch completion event"""
```

## Data Models

### New Event Schemas

#### products.image.masked
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ProductImageMasked",
  "type": "object",
  "required": ["event_id", "job_id", "image_id", "mask_path"],
  "properties": {
    "event_id": {"type": "string"},
    "job_id": {"type": "string"},
    "image_id": {"type": "string"},
    "mask_path": {"type": "string"}
  }
}
```

#### products.images.masked.batch
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ProductImagesMaskedBatch",
  "type": "object",
  "required": ["event_id", "job_id", "total_images"],
  "properties": {
    "event_id": {"type": "string"},
    "job_id": {"type": "string"},
    "total_images": {"type": "integer"}
  }
}
```

#### video.keyframes.masked
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VideoKeyframesMasked",
  "type": "object",
  "required": ["event_id", "job_id", "video_id", "frames"],
  "properties": {
    "event_id": {"type": "string"},
    "job_id": {"type": "string"},
    "video_id": {"type": "string"},
    "frames": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["frame_id", "ts", "mask_path"],
        "properties": {
          "frame_id": {"type": "string"},
          "ts": {"type": "number"},
          "mask_path": {"type": "string"}
        }
      }
    }
  }
}
```

#### video.keyframes.masked.batch
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VideoKeyframesMaskedBatch",
  "type": "object",
  "required": ["event_id", "job_id", "total_keyframes"],
  "properties": {
    "event_id": {"type": "string"},
    "job_id": {"type": "string"},
    "total_keyframes": {"type": "integer"}
  }
}
```

### Database Schema Changes

#### Migration: Add masked_local_path columns
```sql
-- Add masked_local_path to product_images table
ALTER TABLE product_images 
ADD COLUMN masked_local_path VARCHAR(500);

-- Add masked_local_path to video_frames table  
ALTER TABLE video_frames 
ADD COLUMN masked_local_path VARCHAR(500);

-- Add indexes for mask path queries
CREATE INDEX IF NOT EXISTS idx_product_images_masked_path 
ON product_images(masked_local_path) WHERE masked_local_path IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_video_frames_masked_path 
ON video_frames(masked_local_path) WHERE masked_local_path IS NOT NULL;
```

#### Updated Pydantic Models
```python
class ProductImage(BaseModel):
    img_id: str
    product_id: str
    local_path: str
    masked_local_path: Optional[str] = None  # New field
    emb_rgb: Optional[List[float]] = None
    emb_gray: Optional[List[float]] = None
    kp_blob_path: Optional[str] = None
    phash: Optional[int] = None
    created_at: Optional[datetime] = None

class VideoFrame(BaseModel):
    frame_id: str
    video_id: str
    ts: float
    local_path: str
    masked_local_path: Optional[str] = None  # New field
    emb_rgb: Optional[List[float]] = None
    emb_gray: Optional[List[float]] = None
    kp_blob_path: Optional[str] = None
    created_at: Optional[datetime] = None
```

### File System Structure

```
data/
├── masks/
│   ├── products/
│   │   ├── {image_id}.png
│   │   └── ...
│   └── frames/
│       ├── {frame_id}.png
│       └── ...
├── products/
│   └── (existing product images)
└── videos/
    └── (existing video frames)
```

## Error Handling

### Segmentation Failures
- **Strategy**: Continue processing other images, log errors
- **Implementation**: Try-catch around individual image processing
- **Recovery**: Skip failed images, don't block batch completion

### File System Errors
- **Strategy**: Retry with exponential backoff
- **Implementation**: Retry decorator on file operations
- **Recovery**: Fail individual image, continue batch

### Database Errors
- **Strategy**: Retry database updates, use transactions
- **Implementation**: Database connection retry logic
- **Recovery**: Log error, continue processing

### Event Processing Errors
- **Strategy**: Dead letter queue for failed events
- **Implementation**: RabbitMQ DLQ configuration
- **Recovery**: Manual intervention for DLQ messages

### Edge Cases
- **Empty Batches**: Handle batch events with total_images=0 or total_keyframes=0
- **Strategy**: Immediately emit corresponding masked.batch event with count=0
- **Implementation**: Check batch size before processing, emit completion event
- **Missing Files**: Handle cases where referenced image/frame files don't exist
- **Strategy**: Log error, skip processing, continue with batch

### Downstream Service Compatibility
- **Watermark Strategy**: Downstream services wait for masked events with timeout
- **Fallback**: Process raw images if masked events don't arrive within watermark period
- **Graceful Degradation**: System continues to function even if segmentation service is down

## Testing Strategy

### Unit Tests
- **SegmentationEngine**: Mock different segmentation models
- **FileManager**: Test file operations with temporary directories
- **Event Handlers**: Mock database and messaging dependencies
- **Service Logic**: Test batch tracking and completion logic

### Integration Tests
- **Database Integration**: Test schema changes and queries
- **Event Flow**: Test end-to-end event processing
- **File System**: Test mask generation and storage
- **Downstream Compatibility**: Test updated downstream services

### Performance Tests
- **Throughput**: Test concurrent image processing
- **Memory Usage**: Test with large batches
- **Segmentation Speed**: Benchmark different models
- **File I/O**: Test mask storage performance

### Compatibility Tests
- **Backward Compatibility**: Ensure downstream services handle missing masks
- **Event Schema**: Validate new event schemas
- **Database Migration**: Test migration rollback scenarios
- **Service Deployment**: Test rolling deployment scenarios

## Configuration

### Environment Variables
```bash
# Segmentation model configuration
SEGMENTATION_MODEL=rmbg  # rmbg, yolo, sam
SEGMENTATION_MODEL_NAME=briaai/RMBG-1.4  # Hugging Face model name

# Processing configuration
MAX_CONCURRENT_IMAGES=4
BATCH_TIMEOUT_SECONDS=300
MASK_QUALITY=0.8

# File paths
FOREGROUND_MASK_DIR_PATH=data/masks
MODEL_CACHE=/path/to/model/cache  # From common config

# Database and messaging (inherited from common config)
POSTGRES_DSN=postgresql://...
BUS_BROKER=amqp://...
```

### Service Configuration
```python
@dataclass
class ProductSegmentorConfig:
    segmentation_model: str = "rmbg"
    segmentation_model_name: str = "briaai/RMBG-1.4"  # Hugging Face model name
    max_concurrent_images: int = 4
    batch_timeout_seconds: int = 300
    foreground_mask_dir_path: str = "data/masks"
    model_cache: str  # From common config
    
    # Database and messaging
    postgres_dsn: str
    bus_broker: str
```

## Deployment Strategy

### Phase 1: Infrastructure Setup
- Create new service directory structure
- Add database migration for masked_local_path columns
- Create new event schema contracts
- Set up Docker configuration

### Phase 2: Mock Service Deployment
- Deploy skeleton service that listens to *.ready events
- Emit mock *.masked events (copy original paths as mask paths)
- Verify event routing and downstream integration
- No actual segmentation processing

### Phase 3: Downstream Service Updates
- Update vision-embedding service to consume *.masked events
- Update vision-keypoint service to consume *.masked events
- Implement watermark timeout and fallback logic
- Deploy updated downstream services

### Phase 4: Full Segmentation Implementation
- Implement actual segmentation models (starting with RMBG)
- Deploy full segmentation service
- Monitor performance and accuracy
- Gradually increase processing load

### Monitoring and Observability
- Service health monitoring through structured logging
- Processing metrics (images/second, success rate, error rate)
- Segmentation quality metrics (mask coverage, processing time)
- Database migration is additive (no data loss on rollback)