# Matcher Microservice

The Matcher Microservice is the core component of the Product-Video Matching system. Its primary function is to determine if a given e-commerce product is visually present in a specific video frame.

It employs a hybrid computer vision approach:
1.  **Deep Learning Filter (CLIP):** Product and frame images are converted into high-dimensional embeddings. A cosine similarity check is performed as a fast, initial filter. If the similarity is below a threshold, the detailed matching is skipped.
2.  **Traditional Computer Vision Verification (AKAZE/SIFT + RANSAC):** If the CLIP similarity is high, a robust geometric verification is performed using feature matching (AKAZE/SIFT) and RANSAC to find a homography, which confirms the product's presence and provides a precise bounding box.

## Architecture

- **Input:** Consumes matching requests from the `pvm.match.request` RabbitMQ exchange. The request contains product and video frame metadata (including image URLs).
- **Output:** Publishes `MatchResult` objects to the `pvm.match.result` RabbitMQ exchange.
- **Dependencies:** Requires access to a RabbitMQ broker. Uses `opencv-python`, `torch`, and `transformers` for the core vision logic.

## Configuration

The service uses environment variables for configuration, primarily for the RabbitMQ connection details.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost/` | Connection string for the RabbitMQ broker. |
| `MATCH_REQUEST_EXCHANGE` | `pvm.match.request` | Exchange to consume matching requests from. |
| `MATCH_RESULT_EXCHANGE` | `pvm.match.result` | Exchange to publish matching results to. |

## Development

To run the service locally, ensure you have the required Python dependencies installed and a running RabbitMQ instance.

```bash
# Navigate to the service directory
cd services/matcher

# Install dependencies
pip install -r requirements.txt

# Run the service
python main.py
```