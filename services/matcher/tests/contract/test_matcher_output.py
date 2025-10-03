import json
import pytest
from jsonschema import validate  # noqa: F401


@pytest.mark.contract
def test_matcher_output_contract():
    # Load the schema
    with open('O:/product-video-matching/implement-matcher/specs/002-implement-matcher-microservice/contracts/matcher_output.json') as f:
        schema = json.load(f)  # noqa: F841

    # Example of a valid output (this should pass schema validation)
    valid_output = [  # noqa: F841
        {
            "product_id": "prod123",
            "frame_id": "frame456",
            "match_score": 0.85,
            "bounding_box": [10.0, 20.0, 30.0, 40.0],
            "confidence_level": 0.95
        }
    ]

    # This assertion will make the test fail initially, as per TDD
    assert False, "Test is designed to fail until actual implementation is ready"

    # Uncomment the following line once the implementation is ready to pass the contract
    # validate(instance=valid_output, schema=schema)
