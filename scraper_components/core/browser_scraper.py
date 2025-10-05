#!/usr/bin/env python3
"""
Main browser scraper component that orchestrates all scraping operations.

This is the primary interface for browser-based scraping functionality,
coordinating WebDriver management, page validation, product extraction,
and availability checking.
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from .webdriver_manager import WebDriverManager
from .page_validator import PageValidator
from .product_extractor import ProductExtractor
from .availability_checker import AvailabilityChecker
from ..models.product import Product
from ..utils.helpers import get_timestamp


class BrowserScraper:
    """Browser-based scraper that can handle dynamic content."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv('SCRAPING_URL')
        
        # Initialize components
        self.webdriver_manager = WebDriverManager()
        self.page_validator = None
        self.product_extractor = None
        self.availability_checker = None
        
    @property
    def driver(self):
        """Access to the WebDriver instance."""
        return self.webdriver_manager.driver

    def setup_driver(self) -> bool:
        """Setup Chrome driver with recommended options and return success state."""
        success = self.webdriver_manager.setup_driver()
        if success:
            # Initialize components that depend on driver
            self.page_validator = PageValidator(self.driver, self.webdriver_manager)
            self.product_extractor = ProductExtractor(self.driver)
            self.availability_checker = AvailabilityChecker(self.driver, self.page_validator, self.product_extractor, self.webdriver_manager)
        return success

    def scrape_products(self) -> List[Dict[str, Any]]:
        """Main flow: setup driver, load base_url, find product containers, extract info, check availability."""
        try:
            print(f"[{get_timestamp()}] Starting browser-based scrape of store...")
            print(f"URL: {self.base_url}")

            # Setup browser driver
            if not self.setup_driver():
                print(f"[{get_timestamp()}] Failed to setup browser driver.")
                return []

            # Navigate to target page
            print(f"[{get_timestamp()}] Navigating to the page...")
            self.driver.get(self.base_url)

            # Wait for page to be ready
            print(f"[{get_timestamp()}] Waiting for page to be ready...")
            if not self.page_validator.wait_for_page_ready(self.base_url):
                print(f"[{get_timestamp()}] Page failed to load properly")
                return []

            # Take screenshot of main product listing page
            print(f"[{get_timestamp()}] Taking screenshot of product listing page...")
            self.webdriver_manager.take_screenshot("product_listing_page", self.base_url)

            # Extract products from listing page
            print(f"[{get_timestamp()}] Waiting for products to load...")
            product_elements = self.product_extractor.wait_for_products_to_load(timeout=30)

            products = self._extract_products_from_elements(product_elements)
            
            if not products:
                print(f"[{get_timestamp()}] No products found.")
                return []

            # Check availability for each product
            available_products = self._check_products_availability(products)
            
            # Display results
            available_count = len(available_products)
            print(f"[{get_timestamp()}] Browser scraping completed. Found {len(products)} products, {available_count} available.")
            self.display_results(available_products, available_count, len(products))
            
            return available_products

        except Exception as e:
            print(f"[{get_timestamp()}] Browser scraper error: {str(e)}")
            return []
        finally:
            self.webdriver_manager.quit_driver()

    def _extract_products_from_elements(self, product_elements: List) -> List[Product]:
        """Extract product information from web elements."""
        products = []
        if product_elements:
            print(f"[{get_timestamp()}] Extracting information from {len(product_elements)} products...")
            for idx, element in enumerate(product_elements):
                try:
                    product = self.product_extractor.extract_product_info_from_element(element)
                    if product:
                        products.append(product)
                except Exception as e:
                    print(f"[{get_timestamp()}] Error extracting product {idx}: {str(e)}")
                    continue
        return products

    def _check_products_availability(self, products: List[Product]) -> List[Dict[str, Any]]:
        """Check availability for each product and return available ones."""
        available_products = []
        
        print(f"[{get_timestamp()}] Checking availability for {len(products)} products...")
        for product in products:
            if product.url:
                is_available, status, price = self.availability_checker.check_product_availability(product.url)
                
                # Update product with availability information
                product.availability_status = status
                product.is_available = is_available
                product.price = price
                
                if is_available:
                    available_products.append(product.to_dict())
            else:
                product.availability_status = "No URL available"
                product.is_available = False
                product.price = None

        return available_products

    def display_results(self, products: List[Dict[str, Any]], available_count: Optional[int] = None,
                        total_count: Optional[int] = None) -> None:
        """Display the scraped products in a formatted way (keeps original print behavior)."""
        print(f"\n{'='*80}")
        print(f"STORE SCRAPING RESULTS (BROWSER) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        if available_count is not None and total_count is not None:
            print(f"Available products: {available_count}/{total_count}")
            print(f"{'='*80}")

        if not products:
            print("No available products found.")
            return

        for idx, product in enumerate(products, 1):
            print(f"\n{idx}. {product['title']} ({product['price']})")
            if product.get('url'):
                print(f"   URL: {product['url']}")
            if product.get('availability_status'):
                print(f"   Status: {product['availability_status']}")

        print(f"\n{'='*80}")
        print(f"Available products listed: {len(products)}")
        if available_count is not None and total_count is not None:
            print(f"Total products checked: {total_count}")
        print(f"{'='*80}\n")

    # Backward compatibility methods
    def wait_for_page_ready(self, expected_url: Optional[str] = None, timeout: int = 10) -> bool:
        """Backward compatibility wrapper."""
        if self.page_validator:
            return self.page_validator.wait_for_page_ready(expected_url, timeout)
        return False
    
    def validate_page_loaded(self, expected_url: Optional[str]) -> bool:
        """Backward compatibility wrapper."""
        if self.page_validator:
            return self.page_validator.validate_page_loaded(expected_url)
        return False
    
    def wait_for_products_to_load(self, timeout: int = 20) -> List[Any]:
        """Backward compatibility wrapper."""
        if self.product_extractor:
            return self.product_extractor.wait_for_products_to_load(timeout)
        return []
    
    def extract_product_info_from_element(self, element) -> Optional[Dict[str, Any]]:
        """Backward compatibility wrapper."""
        if self.product_extractor:
            product = self.product_extractor.extract_product_info_from_element(element)
            return product.to_dict() if product else None
        return None
    
    def extract_price_from_page(self) -> Optional[str]:
        """Backward compatibility wrapper."""
        if self.product_extractor:
            return self.product_extractor.extract_price_from_page()
        return None
    
    def check_availability_indicators(self) -> tuple:
        """Backward compatibility wrapper."""
        if self.availability_checker:
            return self.availability_checker.check_availability_indicators()
        return False, "Checker not initialized"
    
    def check_quantity_selector_disabled(self) -> bool:
        """Backward compatibility wrapper."""
        if self.availability_checker:
            return self.availability_checker.check_quantity_selector_disabled()
        return False
    
    def check_product_availability(self, product_url: str) -> tuple:
        """Backward compatibility wrapper."""
        if self.availability_checker:
            return self.availability_checker.check_product_availability(product_url)
        return False, "Checker not initialized", None