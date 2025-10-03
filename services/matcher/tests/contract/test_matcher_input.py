import json
import pytest
from jsonschema import validate  # noqa: F401


@pytest.mark.contract
def test_matcher_input_contract():
    # Load the schema
    with open('O:/product-video-matching/implement-matcher/specs/'
              '002-implement-matcher-microservice/contracts/matcher_input.json') as f:
        schema = json.load(f)  # noqa: F841

    # Example of a valid input (this should pass schema validation)
    valid_input = {  # noqa: F841
      "product": {
        "product_id": "prod123",
        "image_url": "http://example.com/product.jpg",
        "metadata": {}
      },
      "video_frame": {
        "frame_id": "frame456",
        "video_id": "video789",
        "timestamp": 123.45,
        "image_url": "http://example.com/frame.jpg"
      }
    }

    # Uncomment the following line once the implementation is ready to pass the contract
    validate(instance=valid_input, schema=schema)
