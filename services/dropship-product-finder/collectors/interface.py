from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IProductCollector(ABC):
    """Interface for all product collectors"""

    @abstractmethod
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for a keyword query; return normalized dicts."""
        raise NotImplementedError
