import json
import pytest
from pathlib import Path
from jsonschema import validate

pytestmark = pytest.mark.contract


def test_matcher_output_contract():
    # Load the schema using relative path to shared contracts
    # Path from services/matcher/tests/contract/ to libs/contracts/contracts/schemas/
    # Need to go up 5 levels from test file to project root, then into libs
    schema_path = Path(__file__).parent.parent.parent.parent.parent / "libs/contracts/contracts/schemas/match_result.json"

    with open(schema_path) as f:
        schema = json.load(f)  # noqa: F841

    # Example of a valid output (this should pass schema validation)
    valid_output = {  # noqa: F841
        "job_id": "job123",
        "product_id": "prod123",
        "video_id": "video456",
        "best_pair": {
            "img_id": "img789",
            "frame_id": "frame456",
            "score_pair": 0.85
        },
        "score": 0.85,
        "ts": 123.45
    }

    # Validate the example output against the schema
    validate(instance=valid_output, schema=schema)
