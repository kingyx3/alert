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


class TestIssue22PageLoadingFix(unittest.TestCase):
    """Test fix for issue #22: Improve page loading stability to prevent false positives."""
    
    def test_buy_indicators_remain_focused(self):
        """Test that BUY_INDICATORS maintains focus on 'buy now' only."""
        from scraper_components.config.constants import BUY_INDICATORS
        
        # Should contain only the specific indicator
        self.assertEqual(BUY_INDICATORS, ['buy now'], 
                        "BUY_INDICATORS should remain focused on 'buy now' to prevent false positives")
    
    def test_page_validator_exists(self):
        """Test that PageValidator has improved stability checking."""
        from scraper_components.core.page_validator import PageValidator
        
        # Verify the class exists and has the required method
        self.assertTrue(hasattr(PageValidator, 'wait_for_page_ready'))
        
        # Check the method signature accepts timeout parameter
        import inspect
        method_sig = inspect.signature(PageValidator.wait_for_page_ready)
        self.assertIn('timeout', method_sig.parameters)


class TestScreenshotFunctionality(unittest.TestCase):
    """Test screenshot functionality for scraper pages."""
    
    def test_webdriver_manager_has_screenshot_method(self):
        """Test that WebDriverManager has screenshot functionality."""
        from scraper_components.core.webdriver_manager import WebDriverManager
        manager = WebDriverManager()
        self.assertTrue(hasattr(manager, 'take_screenshot'))
    
    def test_availability_checker_accepts_webdriver_manager(self):
        """Test that AvailabilityChecker can accept webdriver_manager parameter."""
        from scraper_components.core.availability_checker import AvailabilityChecker
        
        # Mock objects
        mock_driver = None
        mock_validator = None
        mock_extractor = None
        mock_webdriver_manager = None
        
        # Should not raise exception with webdriver_manager parameter
        checker = AvailabilityChecker(mock_driver, mock_validator, mock_extractor, mock_webdriver_manager)
        self.assertEqual(checker.webdriver_manager, mock_webdriver_manager)
    
    def test_screenshot_taken_on_page_load_failure(self):
        """Test that screenshots are taken even when page validation fails."""
        from scraper_components.core.availability_checker import AvailabilityChecker
        from unittest.mock import Mock
        
        # Create mock objects
        mock_driver = Mock()
        mock_page_validator = Mock()
        mock_webdriver_manager = Mock()
        
        # Mock page validation to fail
        mock_page_validator.wait_for_page_ready.return_value = False
        
        # Create availability checker
        checker = AvailabilityChecker(
            driver=mock_driver,
            page_validator=mock_page_validator, 
            webdriver_manager=mock_webdriver_manager
        )
        
        # Call check_product_availability with a test URL
        result = checker.check_product_availability("https://example.com/product")
        
        # Verify that the result indicates failure
        is_available, status, price = result
        self.assertFalse(is_available)
        self.assertEqual(status, "Page failed to load correctly")
        self.assertIsNone(price)
        
        # Verify that screenshots were still taken (twice: once initially, once for failure)
        self.assertEqual(mock_webdriver_manager.take_screenshot.call_count, 2)
        
        # Verify the calls were made with correct parameters
        calls = mock_webdriver_manager.take_screenshot.call_args_list
        self.assertEqual(calls[0][0][0], "product_page")  # First call for regular screenshot
        self.assertEqual(calls[1][0][0], "product_page_failed")  # Second call for failure screenshot
    
    def test_screenshot_taken_on_successful_page_load(self):
        """Test that screenshots are taken when page loads successfully."""
        from scraper_components.core.availability_checker import AvailabilityChecker
        from unittest.mock import Mock
        
        # Create mock objects
        mock_driver = Mock()
        mock_page_validator = Mock()
        mock_webdriver_manager = Mock()
        
        # Mock page validation to succeed
        mock_page_validator.wait_for_page_ready.return_value = True
        
        # Create availability checker with mock product extractor
        checker = AvailabilityChecker(
            driver=mock_driver,
            page_validator=mock_page_validator, 
            webdriver_manager=mock_webdriver_manager
        )
        
        # Mock successful availability check (no buy indicators found)
        mock_driver.page_source = "<html><body>Product not available</body></html>"
        
        # Call check_product_availability with a test URL
        result = checker.check_product_availability("https://example.com/product")
        
        # Verify that the result processes successfully (even if not available)
        is_available, status, price = result
        self.assertFalse(is_available)  # No buy indicators in mock page source
        self.assertIn("Not available", status)
        
        # Verify that screenshot was taken (only once, since page loaded successfully)
        self.assertEqual(mock_webdriver_manager.take_screenshot.call_count, 1)
        
        # Verify the call was made with correct parameters
        calls = mock_webdriver_manager.take_screenshot.call_args_list
        self.assertEqual(calls[0][0][0], "product_page")  # Regular screenshot for successful load
    
    def test_listing_page_screenshot_on_failure(self):
        """Test that listing page screenshots are taken even when page validation fails."""
        from scraper_components.core.browser_scraper import BrowserScraper
        from unittest.mock import Mock, patch
        
        # Create scraper with test URL
        scraper = BrowserScraper("https://example.com")
        
        # Mock the webdriver manager and other components
        mock_webdriver_manager = Mock()
        mock_webdriver_manager.setup_driver.return_value = True
        mock_webdriver_manager.driver = Mock()
        
        mock_page_validator = Mock()
        mock_page_validator.wait_for_page_ready.return_value = False  # Simulate page load failure
        
        scraper.webdriver_manager = mock_webdriver_manager
        scraper.page_validator = mock_page_validator
        
        # Mock the driver property to return the mock driver
        with patch.object(BrowserScraper, 'driver', mock_webdriver_manager.driver):
            result = scraper.scrape_products()
        
        # Verify empty result due to page load failure
        self.assertEqual(result, [])
        
        # Verify that screenshots were taken (twice: once initially, once for failure)
        self.assertEqual(mock_webdriver_manager.take_screenshot.call_count, 2)
        
        # Verify the calls were made with correct parameters
        calls = mock_webdriver_manager.take_screenshot.call_args_list
        self.assertEqual(calls[0][0][0], "product_listing_page")  # First call for regular screenshot
        self.assertEqual(calls[1][0][0], "product_listing_page_failed")  # Second call for failure screenshot


class TestNotificationServiceScraper2Format(unittest.TestCase):
    """Test notification service works directly with scraper2 format."""
    
    def test_notification_service_with_scraper2_format(self):
        """Test that notification service works directly with scraper2 product format."""
        from notification_service import create_notification_service
        
        scraper2_products = [
            {
                "name": "Pokemon TCG Booster Pack",
                "priceShow": "S$4.50",
                "inStock": True,
                "url": "https://example.com/booster-pack",
                "sold": "100+ sold",
                "rating": 4.8
            },
            {
                "name": "Pokemon Collector's Edition",
                "price": 89.99,  # numeric price without priceShow
                "inStock": True,
                "url": "https://example.com/collectors-edition",
            }
        ]
        
        # Test with notification service directly (no normalization needed)
        notification_service = create_notification_service()
        message = notification_service.format_products_text(scraper2_products)
        
        # Should contain product names and prices
        self.assertIn("Pokemon TCG Booster Pack", message)
        self.assertIn("Pokemon Collector's Edition", message)
        self.assertIn("S$4.50", message)  # priceShow format
        self.assertIn("$89.99", message)  # Formatted numeric price
        self.assertIn("Found 2 available products", message)
    
    def test_notification_service_with_numeric_price_fallback(self):
        """Test notification service formats numeric price when priceShow is missing."""
        from notification_service import create_notification_service
        
        scraper2_product = {
            "name": "Test Product",
            "price": 15.75,  # Only numeric price
            "inStock": True,
            "url": "https://example.com/test-product",
        }
        
        notification_service = create_notification_service()
        message = notification_service.format_products_text([scraper2_product])
        
        self.assertIn("Test Product", message)
        self.assertIn("$15.75", message)  # Should format numeric price
        self.assertIn("Found 1 available products", message)
    
    def test_notification_service_with_no_price(self):
        """Test notification service handles products with no price information."""
        from notification_service import create_notification_service
        
        scraper2_product = {
            "name": "No Price Product",
            "inStock": True,
            "url": "https://example.com/no-price",
        }
        
        notification_service = create_notification_service()
        message = notification_service.format_products_text([scraper2_product])
        
        self.assertIn("No Price Product", message)
        self.assertIn("()", message)  # Empty price parentheses
        self.assertIn("Found 1 available products", message)
    
    def test_notification_service_empty_products(self):
        """Test notification service with empty product list."""
        from notification_service import create_notification_service
        
        notification_service = create_notification_service()
        message = notification_service.format_products_text([])
        
        self.assertEqual(message, "🚫 No available products found at this time.")
    
    def test_notification_service_with_sold_count_and_sorting(self):
        """Test notification service displays sold count and sorts products alphabetically."""
        from notification_service import create_notification_service
        
        scraper2_products = [
            {
                "name": "Zebra Product Last",
                "priceShow": "S$10.00",
                "inStock": True,
                "url": "https://example.com/zebra-product",
                "sold": "50 sold",
            },
            {
                "name": "Alpha Product First",
                "priceShow": "S$5.00", 
                "inStock": True,
                "url": "https://example.com/alpha-product",
                "sold": "108 sold",
            },
            {
                "name": "Beta Product Middle",
                "priceShow": "S$7.50",
                "inStock": True,
                "url": "https://example.com/beta-product",
                # No sold count to test missing sold info
            }
        ]
        
        notification_service = create_notification_service()
        message = notification_service.format_products_text(scraper2_products)
        
        # Check alphabetical sorting - Alpha should be first, Beta second, Zebra third
        lines = message.split('\n')
        product_lines = [line for line in lines if '🎯' in line]
        
        self.assertIn('1. 🎯 Alpha Product First', product_lines[0])
        self.assertIn('2. 🎯 Beta Product Middle', product_lines[1]) 
        self.assertIn('3. 🎯 Zebra Product Last', product_lines[2])
        
        # Check sold count display
        self.assertIn('- "108 sold"', message)
        self.assertIn('- "50 sold"', message)
        
        # Check that product without sold count doesn't have dash
        self.assertIn('Beta Product Middle (S$7.50)\n', message)  # No sold count suffix


if __name__ == '__main__':
    unittest.main()