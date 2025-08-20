# Evidence Builder Microservice

## Overview
This microservice is responsible for generating visual evidence of matches between products and video content. It is a key component of the Product-Video Matching System, designed to provide verifiable proof of successful matches.

## Functionality
- Generates visual overlays and annotations on video frames.
- Creates composite images or video clips highlighting matched areas.
- Stores evidence for review and verification.

## In/Out Events
### Input Events
- `MatchFound`: Event indicating a successful match between a product and video segment.
  - Data: `{"match_id": "abc-123", "product_id": "prod-456", "video_id": "vid-789", "timestamp": 123.45}`

### Output Events
- `EvidenceGenerated`: Event indicating that visual evidence has been successfully created.
  - Data: `{"evidence_id": "evd-001", "match_id": "abc-123", "evidence_url": "http://example.com/evidence.png"}`

## Current Progress
- Basic image overlay functionality implemented.
- Integration with storage solutions for evidence files.

## What's Next
- Enhance evidence generation with more sophisticated visual cues.
- Implement video segment extraction for dynamic evidence.
- Optimize evidence generation performance.