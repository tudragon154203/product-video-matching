# Quickstart Guide: Matcher Microservice

This guide provides a quick overview of how to interact with the Matcher Microservice and verify its core functionality.

## 1. Primary User Story
As a system administrator, I want the matcher microservice to accurately identify product matches in video frames so that I can provide relevant video content to users.

## 2. Acceptance Scenarios

### Scenario 1: Successful Match
**Given**: A product image and a video frame where a visual match is expected.
**When**: The matcher microservice processes the product image and video frame data.
**Then**: The microservice should return a JSON response containing:
- A `match_score` (e.g., > 0.7).
- `bounding_box` coordinates indicating the location of the matched product in the video frame.
- A `confidence_level` for the match.

### Scenario 2: No Match Found
**Given**: A product image and a video frame with no visual match.
**When**: The matcher microservice processes the product image and video frame data.
**Then**: The microservice should return a JSON response indicating no match (e.g., an empty list of matches, or a match with a very low `match_score` (e.g., < 0.3)).

## 3. Edge Cases

### Edge Case 1: Poor Quality Product Image
**Given**: A product image of poor quality (e.g., low resolution, blurry).
**When**: The matcher microservice processes this image along with a video frame.
**Then**: The system should still attempt to match, but the returned `confidence_level` and `match_score` may be lower than for high-quality images.

### Edge Case 2: Multiple Products in a Single Frame
**Given**: A product image and a video frame containing multiple instances of the product or multiple different products.
**When**: The matcher microservice processes these inputs.
**Then**: The microservice should identify and return `MatchResult` for all matching products, each with its own `bounding_box`, `match_score`, and `confidence_level`.

### Edge Case 3: Unrecoverable Error During Matching
**Given**: An input that causes an unrecoverable error during the matching process (e.g., corrupted image data).
**When**: The matcher microservice attempts to process this input.
**Then**: The microservice should log the error details and return an appropriate error response, indicating failure without crashing the service.
