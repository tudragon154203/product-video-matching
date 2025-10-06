"""Platform query processing logic extracted from main service."""

from typing import Any, Dict, List, Set


class PlatformQueryProcessor:
    """Handles processing and normalization of platform-specific queries."""

    @staticmethod
    def extract_platform_queries(queries: Any, platforms: List[str]) -> List[str]:
        """Extract and normalize queries for specific platforms.

        Args:
            queries: Query data in various formats (dict, str, list, etc.)
            platforms: List of target platforms

        Returns:
            List of normalized queries for the specified platforms
        """
        if not platforms:
            return []

        if isinstance(queries, dict):
            return PlatformQueryProcessor._process_dict_queries(queries, platforms)

        if isinstance(queries, str):
            return [queries] if queries else []

        if isinstance(queries, (list, tuple, set)):
            return [item for item in queries if item]

        return []

    @staticmethod
    def _process_dict_queries(queries: Dict[str, Any], platforms: List[str]) -> List[str]:
        """Process dictionary-based queries with platform-specific logic."""
        platforms_lower = {platform.lower() for platform in platforms}

        # Prioritize visual content queries for TikTok and YouTube
        if {"tiktok", "youtube"} & platforms_lower:
            prioritized = PlatformQueryProcessor._normalize_to_list(queries.get("vi"))
            if prioritized:
                return prioritized
            return []

        # Aggregate queries from all platforms
        aggregated: List[str] = []
        for value in queries.values():
            aggregated.extend(PlatformQueryProcessor._normalize_to_list(value))

        return PlatformQueryProcessor._dedupe_preserve_order(aggregated)

    @staticmethod
    def _normalize_to_list(value: Any) -> List[str]:
        """Normalize a value to a list of strings."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if item]
        return []

    @staticmethod
    def _dedupe_preserve_order(items: List[str]) -> List[str]:
        """Remove duplicates while preserving order."""
        seen: Set[str] = set()
        result: List[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result