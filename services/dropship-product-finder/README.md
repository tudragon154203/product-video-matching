# Dropship Product Finder Microservice

## Overview
This microservice is responsible for collecting product data from various e-commerce platforms. It is a key component of the Product-Video Matching System, designed to provide product information for matching with video content.

## Functionality
- Collects product data from various e-commerce platforms (e.g., eBay).
- Processes and normalizes product information.
- Publishes product data for further processing.

## In/Out Events
### Input Events
- `ProductCollectionRequest`: Request to initiate product data collection for a specific product or category.
  - Data: `{"source": "ebay", "query": "electronics"}`

### Output Events
- `ProductCollected`: Event indicating that product data has been successfully collected and processed.
  - Data: `{"product_id": "12345", "title": "Example Product", "image_url": "http://example.com/image.jpg"}`

## Current Progress
- Initial setup and basic eBay product collection implemented.
- Data normalization pipeline in progress.

## What's Next
- Integrate with additional e-commerce platforms (e.g., Amazon).
- Implement robust error handling and retry mechanisms.
- Optimize data collection performance.