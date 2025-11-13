# Data Model: Matcher Microservice

## Entities

### Product
- **Description**: Represents an e-commerce product with an associated image.
- **Fields**:
    - `product_id`: string (Unique identifier for the product)
    - `image_url`: string (URL to the product image)
    - `metadata`: object (Additional product information)

### VideoFrame
- **Description**: Represents a single frame extracted from a video.
- **Fields**:
    - `frame_id`: string (Unique identifier for the video frame)
    - `video_id`: string (Identifier for the video the frame belongs to)
    - `timestamp`: float (Timestamp of the frame within the video)
    - `image_url`: string (URL to the video frame image)

### MatchResult
- **Description**: Contains the match score, bounding box, and confidence level for a product-video frame match.
- **Schema**:
```json
{
  "type": "object",
  "properties": {
    "product_id": {"type": "string", "description": "ID of the matched product"},
    "frame_id": {"type": "string", "description": "ID of the video frame"},
    "match_score": {"type": "number", "format": "float", "description": "Overall match score"},
    "bounding_box": {
      "type": "array",
      "items": {"type": "number", "format": "float"},
      "minItems": 4,
      "maxItems": 4,
      "description": "[x_min, y_min, x_max, y_max] coordinates of the bounding box"
    },
    "confidence_level": {"type": "number", "format": "float", "description": "Confidence level of the match"}
  },
  "required": ["product_id", "frame_id", "match_score", "bounding_box", "confidence_level"]
}
```