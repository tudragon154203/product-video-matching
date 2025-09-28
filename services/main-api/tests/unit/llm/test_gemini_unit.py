"""
Unit tests for the Gemini service without requiring API access.
"""
from services.llm.prompt_service import PromptService
import pytest
import sys
import os

# Add the libs directory to the path
sys.path.append(os.path.join(os.path.dirname(
    __file__), "..", "..", "..", "libs"))

# Add the current directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.unit


def test_build_cls_prompt():
    """Test building classification prompt."""
    prompt_service = PromptService()
    query = "ergonomic office chair"
    labels = ["office_products", "electronics", "fashion"]

    prompt = prompt_service.build_cls_prompt(query, labels)

    assert query in prompt
    for label in labels:
        assert label in prompt


def test_build_gen_prompt():
    """Test building generation prompt."""
    prompt_service = PromptService()
    query = "ergonomic office chair"
    industry = "office_products"

    prompt = prompt_service.build_gen_prompt(query, industry)

    assert query in prompt
    assert industry in prompt
    assert "JSON" in prompt


def test_normalize_queries():
    """Test query normalization."""
    prompt_service = PromptService()

    # Test normal case
    queries = {
        "product": {"en": ["query1", "query2", "query3"]},
        "video": {
            "vi": ["video1", "video2"],
            "zh": ["视频1", "视频2"]
        }
    }

    normalized = prompt_service.normalize_queries(queries)

    assert "product" in normalized
    assert "video" in normalized
    assert len(normalized["product"]["en"]) == 3
    assert len(normalized["video"]["vi"]) == 2
    assert len(normalized["video"]["zh"]) == 2


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])
