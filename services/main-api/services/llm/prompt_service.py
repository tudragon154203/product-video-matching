from typing import Dict, Any, List

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

    def normalize_queries(self, queries: Dict[str, Any], min_items: int = 2, max_items: int = 4) -> Dict[str, Any]:
        """Normalize generated queries to ensure they meet requirements."""
        normalized = {
            "product": {"en": []},
            "video": {"vi": [], "zh": []}
        }
        
        if "product" in queries and "en" in queries["product"]:
            en_queries = queries["product"]["en"][:max_items]
            if len(en_queries) < min_items and len(en_queries) > 0:
                en_queries.extend([en_queries[0]] * (min_items - len(en_queries)))
            try:
                normalized["product"]["en"] = [q if isinstance(q, str) else str(q) for q in en_queries]
            except Exception:
                normalized["product"]["en"] = []
        
        if "video" in queries and "vi" in queries["video"]:
            vi_queries = queries["video"]["vi"][:max_items]
            if len(vi_queries) < min_items and len(vi_queries) > 0:
                vi_queries.extend([vi_queries[0]] * (min_items - len(vi_queries)))
            try:
                normalized["video"]["vi"] = [q if isinstance(q, str) else str(q) for q in vi_queries]
            except Exception:
                normalized["video"]["vi"] = []
        
        if "video" in queries and "zh" in queries["video"]:
            zh_queries = queries["video"]["zh"][:max_items]
            if len(zh_queries) < min_items and len(zh_queries) > 0:
                zh_queries.extend([zh_queries[0]] * (min_items - len(zh_queries)))
            try:
                normalized["video"]["zh"] = [q if isinstance(q, str) else str(q) for q in zh_queries]
            except Exception:
                normalized["video"]["zh"] = []
        
        return normalized

    def route_video_queries(self, queries: Dict[str, Any], platforms: list) -> Dict[str, list]:
        """Route video queries based on platforms, ensuring both vi and zh are present."""
        video_queries = {
            "vi": [],
            "zh": []
        }
        if "youtube" in platforms and "vi" in queries["video"]:
            video_queries["vi"] = queries["video"]["vi"]
        if "douyin" in platforms and "vi" in queries["video"]:
            video_queries["vi"] = queries["video"]["vi"]
        if "tiktok" in platforms and "vi" in queries["video"]:
            video_queries["vi"] = queries["video"]["vi"]
        if "bilibili" in platforms and "zh" in queries["video"]:
            video_queries["zh"] = queries["video"]["zh"]
        return video_queries