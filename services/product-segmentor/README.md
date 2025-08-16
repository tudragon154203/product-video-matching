# Product Segmentor Service

The Product Segmentor Service is a microservice that generates product-focused masks for both catalog images and video keyframes. It sits between the collection phase and feature extraction phase in the product-video matching pipeline.

## Purpose

- Process product catalog images to generate masks that focus on product regions
- Process video keyframes to generate masks that isolate products from backgrounds
- Improve downstream feature extraction accuracy by masking out people, backgrounds, and distracting elements
- Emit masked events that downstream services consume instead of raw image events

## Architecture

The service follows the established event-driven microservice pattern:

- **Input Events**: `products.images.ready`, `products.images.ready.batch`, `videos.keyframes.ready`, `videos.keyframes.ready.batch`
- **Output Events**: `products.image.masked`, `products.images.masked.batch`, `video.keyframes.masked`, `video.keyframes.masked.batch`
- **Segmentation Models**: Pluggable interface supporting RMBG, YOLO, SAM models
- **Storage**: Masks saved to `data/masks/products/` and `data/masks/frames/`

## Configuration

Environment variables:

```bash
# Segmentation model
SEGMENTATION_MODEL=rmbg
SEGMENTATION_MODEL_NAME=briaai/RMBG-1.4

# Processing
MAX_CONCURRENT_IMAGES=4
BATCH_TIMEOUT_SECONDS=300
MASK_QUALITY=0.8

# Paths
MASK_BASE_PATH=data/masks
MODEL_CACHE=/path/to/model/cache

# Database and messaging
POSTGRES_DSN=postgresql://user:pass@host:port/db
BUS_BROKER=amqp://user:pass@host:port/
```

## Development

### Setup

```bash
cd services/product-segmentor
pip install -r requirements.txt
```

### Testing

```bash
pytest tests/
```

### Running

```bash
python main.py
```

## Docker

The service includes Docker configuration for containerized deployment following the established patterns used by other services in the system.