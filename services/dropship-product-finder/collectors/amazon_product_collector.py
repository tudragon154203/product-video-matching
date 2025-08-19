from .mock_product_collector import MockProductCollector


class AmazonProductCollector(MockProductCollector):
    """Amazon product collector (currently mock implementation)"""
    
    def get_source_name(self) -> str:
        """Return the source name"""
        return "amazon"