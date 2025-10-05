from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EbayProduct:
    """Represents a normalized eBay product."""
    id: str
    title: str
    brand: Optional[str]
    url: Optional[str]
    images: List[str] = field(default_factory=list)
    marketplace: str
    price: float
    currency: str
    epid: Optional[str]
    itemId: str
    totalPrice: float
    shippingCost: float
