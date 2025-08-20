# Product Segmentor Microservice

## Overview
This microservice is responsible for segmenting products within images or video frames. It helps isolate the product for more accurate feature extraction and matching.

## Functionality
- Identifies and segments product regions in images.
- Generates masks or bounding boxes for detected products.
- Pre-processes images for downstream vision tasks.

## In/Out Events
### Input Events
- `ImageForSegmentation`: Event containing an image or frame requiring product segmentation.
  - Data: `{"image_id": "img-001", "image_url": "http://example.com/image.jpg"}`

### Output Events
- `ProductSegmented`: Event indicating that a product has been successfully segmented.
  - Data: `{"image_id": "img-001", "segmentation_mask_url": "http://example.com/mask.png", "bounding_box": [x1, y1, x2, y2]}`

## Current Progress
- Basic product segmentation using pre-trained models.
- Integration with image processing pipeline.

## What's Next
- Improve segmentation accuracy and robustness.
- Explore real-time segmentation for video streams.
- Integrate with different segmentation models.