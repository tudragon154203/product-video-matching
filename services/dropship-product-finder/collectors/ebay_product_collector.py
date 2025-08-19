from .mock_product_collector import MockProductCollector


class EbayProductCollector(MockProductCollector):
    """eBay product collector (mock implementation for development)"""
    
    def get_source_name(self) -> str:
        """Return the source name"""
        return "ebay"