"""
Test script for the main API service.
"""
import asyncio
import json
import sys
import os

# Add the libs directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

# Add the current directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from config_loader import config
from main import call_ollama, build_cls_prompt, build_gen_prompt, normalize_queries

async def test_ollama_integration():
    """Test Ollama integration."""
    try:
        print("Testing Ollama integration...")
        
        # Use current config
        print(f"Loaded config: OLLAMA_HOST={config.OLLAMA_HOST}")
        
        # Set OLLAMA_HOST for the ollama client
        os.environ["OLLAMA_HOST"] = config.OLLAMA_HOST
        
        # Test query
        test_query = "ergonomic office chair"
        industry_labels = config.INDUSTRY_LABELS
        
        print("\n1. Testing industry classification...")
        cls_prompt = build_cls_prompt(test_query, industry_labels)
        
        try:
            cls_response = await call_ollama(
                model=config.OLLAMA_MODEL_CLASSIFY,
                prompt=cls_prompt,
                timeout_s=config.OLLAMA_TIMEOUT
            )
            industry = cls_response["response"].strip()
            print(f"Industry: {industry}")
            assert industry in industry_labels, f"Industry '{industry}' not in allowed labels"
        except Exception as e:
            print(f"Error in industry classification: {e}")
            return False
        
        print("\n2. Testing query generation...")
        gen_prompt = build_gen_prompt(test_query, industry)
        
        try:
            gen_response = await call_ollama(
                model=config.OLLAMA_MODEL_GENERATE,
                prompt=gen_prompt,
                timeout_s=config.OLLAMA_TIMEOUT,
                options={"num_ctx": 4096}
            )
            queries = json.loads(gen_response["response"])
            print(f"Generated queries: {json.dumps(queries, indent=2)}")
            
            # Normalize and validate
            normalized = normalize_queries(queries)
            assert "product" in normalized, "Missing 'product' key"
            assert "video" in normalized, "Missing 'video' key"
            assert "en" in normalized["product"], "Missing 'en' in product queries"
            assert "vi" in normalized["video"] or "zh" in normalized["video"], "Missing video queries for platforms"
            
        except Exception as e:
            print(f"Error in query generation: {e}")
            return False
        
        print("\nAll tests passed!")
        return True
    except Exception as e:
        print(f"Unexpected error in test: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_ollama_integration())
        exit_code = 0 if result else 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit_code = 1
    exit(exit_code)