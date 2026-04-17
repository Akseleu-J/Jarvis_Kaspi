from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Product:
    title: str
    price: float
    url: str
    source: str
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    seller: Optional[str] = None
    available: bool = True
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None

    @property
    def formatted_price(self) -> str:
        return f"{self.price:,.0f} ₸"

    @property
    def short_title(self) -> str:
        if len(self.title) > 60:
            return self.title[:57] + "..."
        return self.title

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "url": self.url,
            "source": self.source,
            "image_url": self.image_url,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "seller": self.seller,
            "available": self.available,
        }

    @classmethod
    def from_scrape(
        cls,
        title: str,
        price: float,
        url: str,
        source: str = "kaspi",
        image_url: Optional[str] = None,
        rating: Optional[float] = None,
        reviews_count: Optional[int] = None,
        seller: Optional[str] = None,
    ) -> Product:
        return cls(
            title=title,
            price=price,
            url=url,
            source=source,
            image_url=image_url,
            rating=rating,
            reviews_count=reviews_count,
            seller=seller,
        )
