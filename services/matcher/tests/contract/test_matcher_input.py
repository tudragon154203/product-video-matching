import json
import os
import pytest
from pathlib import Path
from jsonschema import validate  # noqa: F401

pytestmark = pytest.mark.contract


def test_matcher_input_contract():
    # Load the schema using relative path to shared contracts
    # Path from services/matcher/tests/contract/ to libs/contracts/contracts/schemas/
    # Need to go up 5 levels from test file to project root, then into libs
    schema_path = Path(__file__).parent.parent.parent.parent.parent / "libs/contracts/contracts/schemas/match_request.json"

    with open(schema_path) as f:
        schema = json.load(f)  # noqa: F841

    # Example of a valid input (this should pass schema validation)
    valid_input = {  # noqa: F841
      "job_id": "job123",
      "event_id": "550e8400-e29b-41d4-a716-446655440000"
    }

    # Validate the actual service contract
    validate(instance=valid_input, schema=schema)
