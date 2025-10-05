#!/usr/bin/env python3
"""
Product data model for representing scraped product information.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Product:
    """Represents a product with availability and pricing information."""
    
    title: str
    url: str = ""
    image: str = ""
    price: Optional[str] = None
    availability_status: str = "Unknown"
    is_available: bool = False
    scraped_at: str = ""
    
    def __post_init__(self):
        """Set scraped_at timestamp if not provided."""
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary format."""
        return {
            'title': self.title,
            'url': self.url,
            'image': self.image,
            'price': self.price,
            'availability_status': self.availability_status,
            'is_available': self.is_available,
            'scraped_at': self.scraped_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Create product from dictionary data."""
        return cls(
            title=data.get('title', 'No title available'),
            url=data.get('url', ''),
            image=data.get('image', ''),
            price=data.get('price'),
            availability_status=data.get('availability_status', 'Unknown'),
            is_available=data.get('is_available', False),
            scraped_at=data.get('scraped_at', datetime.now().isoformat())
        )