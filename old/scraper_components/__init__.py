"""
Web scraping package for product availability monitoring.

This package provides modular components for scraping e-commerce websites
and checking product availability.
"""

from .core.browser_scraper import BrowserScraper
from .models.product import Product

__all__ = ['BrowserScraper', 'Product']