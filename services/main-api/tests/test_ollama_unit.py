"""
Unit tests for the Ollama-related functions.
"""
import sys
import os
import json

# Add the libs directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

# Add the current directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from services.prompt_service import PromptService

def test_build_cls_prompt():
    """Test the build_cls_prompt function."""
    prompt_service = PromptService()
    test_query = "ergonomic office chair"
    industry_labels = ["fashion", "electronics", "home_garden"]
    
    prompt = prompt_service.build_cls_prompt(test_query, industry_labels)
    
    assert "ergonomic office chair" in prompt
    assert "fashion,electronics,home_garden" in prompt
    assert "Classify this query into one industry label" in prompt
    assert "Output only the label name" in prompt
    
    print("PASSED: build_cls_prompt test passed")

def test_build_gen_prompt():
    """Test the build_gen_prompt function."""
    prompt_service = PromptService()
    test_query = "ergonomic office chair"
    industry = "home_garden"
    
    prompt = prompt_service.build_gen_prompt(test_query, industry)
    
    assert "ergonomic office chair" in prompt
    assert "home_garden" in prompt
    assert "Generate search queries in JSON format" in prompt
    assert "Output JSON format" in prompt
    assert "Rules:" in prompt
    
    print("PASSED: build_gen_prompt test passed")

def test_normalize_queries():
    """Test the normalize_queries function."""
    prompt_service = PromptService()
    
    # Test with valid queries
    queries = {
        "product": {"en": ["office chair", "ergonomic chair", "desk chair"]},
        "video": {
            "vi": ["ghế văn phòng", "ghế công thái học"],
            "zh": ["办公椅", "人体工学椅"]
        }
    }
    
    normalized = prompt_service.normalize_queries(queries)
    
    assert "product" in normalized
    assert "video" in normalized
    assert len(normalized["product"]["en"]) == 3
    assert len(normalized["video"]["vi"]) == 2
    assert len(normalized["video"]["zh"]) == 2
    
    # Test with empty queries
    empty_queries = {}
    normalized_empty = prompt_service.normalize_queries(empty_queries)
    
    assert "product" in normalized_empty
    assert "video" in normalized_empty
    assert normalized_empty["product"]["en"] == []
    assert normalized_empty["video"]["vi"] == []
    assert normalized_empty["video"]["zh"] == []
    
    print("PASSED: normalize_queries test passed")

if __name__ == "__main__":
    try:
        test_build_cls_prompt()
        test_build_gen_prompt()
        test_normalize_queries()
        print("\nAll unit tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)