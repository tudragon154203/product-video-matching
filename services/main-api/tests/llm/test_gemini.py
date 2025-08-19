"""
Test script for the Gemini integration in the main API service.
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
from services.llm.llm_service import LLMService
from services.llm.prompt_service import PromptService

async def test_gemini_integration():
    """Test Gemini integration."""
    try:
        print("Testing Gemini integration...")
        
        # Check if GEMINI_API_KEY is set
        if not config.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY is not set in the configuration.")
            print("To run this test successfully, please set GEMINI_API_KEY in your .env file.")
            return True  # Return True since this is an environment issue, not a code issue
        
        print(f"Loaded config: GEMINI_API_KEY={'*' * len(config.GEMINI_API_KEY) if config.GEMINI_API_KEY else 'NOT SET'}")
        print(f"Loaded config: GEMINI_MODEL={config.GEMINI_MODEL}")
        
        # Create service instances
        llm_service = LLMService()
        prompt_service = PromptService()
        
        # Test query
        test_query = "ergonomic office chair"
        industry_labels = config.INDUSTRY_LABELS
        
        print("\n1. Testing industry classification...")
        cls_prompt = prompt_service.build_cls_prompt(test_query, industry_labels)
        
        try:
            cls_response = await llm_service.call_gemini(
                model=config.GEMINI_MODEL,
                prompt=cls_prompt,
                timeout_s=config.LLM_TIMEOUT
            )
            industry = cls_response["response"].strip()
            print(f"Industry: {industry}")
            assert industry in industry_labels, f"Industry '{industry}' not in allowed labels"
        except Exception as e:
            print(f"Error in industry classification: {e}")
            return False
        
        print("\n2. Testing query generation...")
        gen_prompt = prompt_service.build_gen_prompt(test_query, industry)
        
        try:
            gen_response = await llm_service.call_gemini(
                model=config.GEMINI_MODEL,
                prompt=gen_prompt,
                timeout_s=config.LLM_TIMEOUT
            )
            # Try to parse the response as JSON
            try:
                queries = json.loads(gen_response["response"])
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the response
                # This can happen with Gemini as it sometimes includes additional text
                response_text = gen_response["response"]
                # Find the first '{' and last '}' to extract JSON
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = response_text[start:end]
                    queries = json.loads(json_str)
                else:
                    raise ValueError(f"Could not extract JSON from response: {response_text}")
            
            # Try to print the generated queries, handling encoding issues
            try:
                print(f"Generated queries: {json.dumps(queries, indent=2, ensure_ascii=False)}")
            except UnicodeEncodeError:
                # If there's an encoding issue, print with ascii encoding
                print(f"Generated queries: {json.dumps(queries, indent=2, ensure_ascii=True)}")
            
            # Normalize and validate
            normalized = prompt_service.normalize_queries(queries)
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
        result = asyncio.run(test_gemini_integration())
        exit_code = 0 if result else 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit_code = 1
    exit(exit_code)