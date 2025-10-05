#!/usr/bin/env python3
"""
Basic tests for refactored scraper components.

Tests component imports, initialization, and basic functionality.
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestComponentImports(unittest.TestCase):
    """Test that all components can be imported correctly."""
    
    def test_browser_scraper_import(self):
        """Test BrowserScraper can be imported."""
        from scraper_components.core.browser_scraper import BrowserScraper
        scraper = BrowserScraper()
        self.assertIsNotNone(scraper)
    
    def test_product_model_import(self):
        """Test Product model can be imported and used."""
        from scraper_components.models.product import Product
        
        product = Product(title="Test Product", url="http://example.com")
        self.assertEqual(product.title, "Test Product")
        self.assertEqual(product.url, "http://example.com")
        self.assertFalse(product.is_available)
    
    def test_constants_import(self):
        """Test configuration constants can be imported."""
        from scraper_components.config.constants import PRODUCT_SELECTORS, PRICE_SELECTORS
        
        self.assertIsInstance(PRODUCT_SELECTORS, list)
        self.assertIsInstance(PRICE_SELECTORS, list)
        self.assertGreater(len(PRODUCT_SELECTORS), 0)
        self.assertGreater(len(PRICE_SELECTORS), 0)
    
    def test_helpers_import(self):
        """Test helper functions can be imported and used."""
        from scraper_components.utils.helpers import get_timestamp, normalize_url, is_valid_price_text
        
        timestamp = get_timestamp()
        self.assertIsInstance(timestamp, str)
        
        # Test URL normalization
        self.assertEqual(normalize_url('http://example.com'), 'http://example.com')
        self.assertEqual(normalize_url('/path'), 'https://www.lazada.sg/path')
        self.assertEqual(normalize_url('//example.com'), 'https://example.com')
        
        # Test price validation
        self.assertTrue(is_valid_price_text('$19.99'))
        self.assertTrue(is_valid_price_text('S$29.50'))
        self.assertFalse(is_valid_price_text('No price'))
        self.assertFalse(is_valid_price_text(''))


class TestBackwardCompatibility(unittest.TestCase):
    """Test that backward compatibility is maintained."""
    
    def test_scraper_import(self):
        """Test that the main scraper module imports work."""
        from scraper import BrowserScraper, PRODUCT_SELECTORS, _now
        
        # Test BrowserScraper
        scraper = BrowserScraper()
        self.assertIsNotNone(scraper)
        
        # Test constants
        self.assertIsInstance(PRODUCT_SELECTORS, list)
        self.assertGreater(len(PRODUCT_SELECTORS), 0)
        
        # Test helper function
        timestamp = _now()
        self.assertIsInstance(timestamp, str)
    
    def test_component_methods_available(self):
        """Test that all expected methods are available on BrowserScraper."""
        from scraper import BrowserScraper
        
        scraper = BrowserScraper()
        
        # Test that key methods exist
        expected_methods = [
            'setup_driver', 'scrape_products', 'display_results',
            'wait_for_page_ready', 'validate_page_loaded',
            'wait_for_products_to_load', 'extract_product_info_from_element',
            'extract_price_from_page', 'check_availability_indicators',
            'check_quantity_selector_disabled', 'check_product_availability'
        ]
        
        for method_name in expected_methods:
            self.assertTrue(hasattr(scraper, method_name), 
                          f"Method {method_name} not found on BrowserScraper")
            self.assertTrue(callable(getattr(scraper, method_name)),
                          f"Attribute {method_name} is not callable")


class TestProductModel(unittest.TestCase):
    """Test the Product data model."""
    
    def test_product_creation(self):
        """Test Product creation and default values."""
        from scraper_components.models.product import Product
        
        product = Product(title="Test Product")
        
        self.assertEqual(product.title, "Test Product")
        self.assertEqual(product.url, "")
        self.assertEqual(product.image, "")
        self.assertIsNone(product.price)
        self.assertEqual(product.availability_status, "Unknown")
        self.assertFalse(product.is_available)
        self.assertIsNotNone(product.scraped_at)
    
    def test_product_to_dict(self):
        """Test Product to_dict method."""
        from scraper_components.models.product import Product
        
        product = Product(
            title="Test Product",
            url="http://example.com",
            price="$19.99",
            is_available=True
        )
        
        product_dict = product.to_dict()
        
        self.assertIsInstance(product_dict, dict)
        self.assertEqual(product_dict['title'], "Test Product")
        self.assertEqual(product_dict['url'], "http://example.com")
        self.assertEqual(product_dict['price'], "$19.99")
        self.assertTrue(product_dict['is_available'])
    
    def test_product_from_dict(self):
        """Test Product from_dict class method."""
        from scraper_components.models.product import Product
        
        data = {
            'title': 'Test Product',
            'url': 'http://example.com',
            'price': '$29.99',
            'is_available': True,
            'availability_status': 'In Stock'
        }
        
        product = Product.from_dict(data)
        
        self.assertEqual(product.title, 'Test Product')
        self.assertEqual(product.url, 'http://example.com')
        self.assertEqual(product.price, '$29.99')
        self.assertTrue(product.is_available)
        self.assertEqual(product.availability_status, 'In Stock')


class TestIssue22AvailabilityFix(unittest.TestCase):
    """Test fix for issue #22: Expand availability detection indicators."""
    
    def test_expanded_buy_indicators(self):
        """Test that BUY_INDICATORS now includes common purchase terms."""
        from scraper_components.config.constants import BUY_INDICATORS
        
        # Should include the original indicator
        self.assertIn('buy now', BUY_INDICATORS)
        
        # Should now include common alternatives
        expected_indicators = ['buy', 'add to cart', 'purchase', 'order', 'checkout']
        for indicator in expected_indicators:
            self.assertIn(indicator, BUY_INDICATORS, 
                         f"Missing common indicator: {indicator}")
        
        # Should have more than just 'buy now'
        self.assertGreater(len(BUY_INDICATORS), 1, 
                          "BUY_INDICATORS should contain multiple terms")


if __name__ == '__main__':
    unittest.main()