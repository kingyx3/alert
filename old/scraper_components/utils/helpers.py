#!/usr/bin/env python3
"""
Helper utility functions for web scraping operations.
"""

from datetime import datetime
from typing import Optional


def get_timestamp() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().isoformat()


def safe_get_attribute(elem, attr: str) -> Optional[str]:
    """Return element attribute value or None safely."""
    try:
        return elem.get_attribute(attr)
    except Exception:
        return None


def normalize_url(url: str, base_domain: str = 'https://www.lazada.sg') -> str:
    """Normalize relative URLs to absolute URLs."""
    if not url:
        return ""
    
    if url.startswith('http'):
        return url
    elif url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return base_domain + url
    else:
        return url


def is_valid_price_text(text: str) -> bool:
    """Check if text contains valid price indicators."""
    if not text or len(text) > 50:
        return False
    
    price_symbols = ['$', '₹', '€', '£', '¥', 'S$', 'USD', 'SGD']
    return any(symbol in text for symbol in price_symbols)