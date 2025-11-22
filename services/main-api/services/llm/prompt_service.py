import json
import re
from typing import Dict, Any, List, Union
from common_py.logging_config import configure_logging

logger = configure_logging("main-api:prompt_service")


class PromptService:
    def build_cls_prompt(self, query: str, industry_labels: list) -> str:
        """Build prompt for industry classification."""
        labels_csv = ",".join(industry_labels)
        return f"""Classify this query into one industry label from the list:

Query: {query}
Labels: {labels_csv}

Output only the label name, nothing else."""

    def build_gen_prompt(self, query: str, industry: str) -> str:
        """Build prompt for query generation."""
        return f"""Generate search queries in JSON format:

Input query: {query}
Industry: {industry}

Output JSON format:
{{
  "product": {{ "en": [queries] }},
  "video": {{ "vi": [queries], "zh": [queries] }}
}}

Rules:
- 2-4 English product queries
- 2-4 Vietnamese video queries (with diacritics/accents, e.g., "hế" not "he")
- 2-4 Chinese video queries
- Output only JSON, no additional text"""

    def normalize_queries(self, queries: Union[Dict[str, Any], str], min_items: int = 2, max_items: int = 4) -> Dict[str, Any]:
        """Normalize generated queries to ensure they meet requirements.

        Args:
            queries: Either a parsed dictionary or raw string response from LLM
            min_items: Minimum number of queries required per category
            max_items: Maximum number of queries allowed per category

        Returns:
            Normalized dictionary with proper query structure
        """
        # Handle string responses (malformed JSON from LLM)
        if isinstance(queries, str):
            try:
                # Clean the string response before parsing
                cleaned_response = self._clean_llm_response(queries)
                queries = json.loads(cleaned_response)
            except (json.JSONDecodeError, Exception) as e:
                # If parsing fails, create fallback structure
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                return self._create_fallback_queries(min_items)

        normalized = {
            "product": {"en": []},
            "video": {"vi": [], "zh": []}
        }

        # Handle product queries (English)
        if "product" in queries and "en" in queries["product"]:
            en_queries = self._process_query_list(
                queries["product"]["en"], min_items, max_items)
            normalized["product"]["en"] = en_queries

        # Handle video queries (Vietnamese)
        if "video" in queries and "vi" in queries["video"]:
            vi_queries = self._process_query_list(
                queries["video"]["vi"], min_items, max_items)
            normalized["video"]["vi"] = vi_queries

        # Handle video queries (Chinese)
        if "video" in queries and "zh" in queries["video"]:
            zh_queries = self._process_query_list(
                queries["video"]["zh"], min_items, max_items)
            normalized["video"]["zh"] = zh_queries

        return normalized

    def _clean_llm_response(self, response: str) -> str:
        """Clean LLM response by removing extra formatting and extracting JSON."""
        # Remove common prefixes like "json", "JSON", "```json", etc.
        response = re.sub(r'^\s*(json|JSON)?\s*', '', response, count=1)

        # Remove markdown code block wrappers
        response = re.sub(r'^```json\s*', '', response, count=1)
        response = re.sub(r'\s*```\s*$', '', response, count=1)

        # Remove extra whitespace and newlines
        response = re.sub(r'\s+', ' ', response).strip()

        return response

    def _process_query_list(self, queries: Union[List[str], str], min_items: int, max_items: int) -> List[str]:
        """Process a list of queries, ensuring proper format and quantity."""
        # Handle case where queries might be a single string instead of list
        if isinstance(queries, str):
            queries = [queries]

        # Ensure it's a list and filter out non-string items
        query_list = []
        for q in queries:
            if isinstance(q, str) and q.strip():
                query_list.append(q.strip())

        # Limit to max items
        query_list = query_list[:max_items]

        # Ensure minimum number of items
        if len(query_list) < min_items and len(query_list) > 0:
            query_list.extend([query_list[0]] * (min_items - len(query_list)))

        return query_list

    def _create_fallback_queries(self, min_items: int) -> Dict[str, Any]:
        """Create fallback query structure when LLM response parsing fails."""
        return {
            "product": {"en": [""] * min_items},
            "video": {"vi": [""] * min_items, "zh": [""] * min_items}
        }

    def route_video_queries(self, queries: Dict[str, Any], platforms: list) -> Dict[str, list]:
        """Route video queries based on platforms, ensuring at least one language is present."""
        video_queries = {}
        
        # Map platforms to their primary languages
        vi_platforms = {"youtube", "tiktok"}
        zh_platforms = {"bilibili", "douyin"}
        
        platforms_lower = {p.lower() for p in platforms}
        
        # Add vi queries if relevant platforms are selected
        if vi_platforms & platforms_lower and "vi" in queries.get("video", {}):
            video_queries["vi"] = queries["video"]["vi"]
        
        # Add zh queries if relevant platforms are selected
        if zh_platforms & platforms_lower and "zh" in queries.get("video", {}):
            video_queries["zh"] = queries["video"]["zh"]
        
        # Ensure at least one language is present (fallback)
        if not video_queries:
            # If no platform-specific match, include whatever is available
            if "vi" in queries.get("video", {}):
                video_queries["vi"] = queries["video"]["vi"]
            if "zh" in queries.get("video", {}):
                video_queries["zh"] = queries["video"]["zh"]
        
        return video_queries
