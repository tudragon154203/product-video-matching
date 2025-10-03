import json
import pytest
from jsonschema import validate  # noqa: F401

pytestmark = pytest.mark.contract


def test_matcher_input_contract():
    # Load the schema
    with open('O:/product-video-matching/implement-matcher/libs/contracts/'
              'contracts/schemas/match_request.json') as f:
        schema = json.load(f)  # noqa: F841

    # Example of a valid input (this should pass schema validation)
    valid_input = {  # noqa: F841
      "job_id": "job123",
      "event_id": "550e8400-e29b-41d4-a716-446655440000"
    }

    # Validate the actual service contract
    validate(instance=valid_input, schema=schema)
