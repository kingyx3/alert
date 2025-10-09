#!/usr/bin/env python3
"""
Purchase workflow module for automated product purchasing.

This module provides a workflow function that can be triggered when scraper.py
detects available products. It uses selenium-based browser automation to
navigate to product pages and attempt to click "Buy Now" buttons.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Import the selenium components from scraper_old.py infrastructure
from scraper_components.core.webdriver_manager import WebDriverManager
from scraper_components.core.page_validator import PageValidator
from scraper_components.utils.helpers import get_timestamp, normalize_url

try:
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    class By:
        CSS_SELECTOR = "css selector"
        TAG_NAME = "tag name"
    class NoSuchElementException(Exception):
        pass


# Buy Now button selectors (extracted from constants)
BUY_NOW_SELECTORS = [
    '[data-qa-locator*="buy-now"]',
    '[data-testid*="buy-now"]',
    '.buy-now-button',
    '.buy-now',
    'button[class*="buy-now"]',
    'a[class*="buy-now"]',
    '[data-qa-locator*="add-to-cart"]',
    '[data-testid*="add-to-cart"]',
    '.add-to-cart-button',
    '.add-to-cart',
    'button[class*="add-to-cart"]',
    'a[class*="add-to-cart"]'
]


class PurchaseWorkflow:
    """Handles automated product purchasing using selenium browser automation."""
    
    def __init__(self):
        self.webdriver_manager = None
        self.page_validator = None
        self.driver = None
    
    def setup_browser(self) -> bool:
        """Setup the browser driver for purchasing."""
        if not SELENIUM_AVAILABLE:
            print(f"[{get_timestamp()}] Selenium is not available for purchase workflow")
            return False
        
        self.webdriver_manager = WebDriverManager()
        success = self.webdriver_manager.setup_driver()
        
        if success:
            self.driver = self.webdriver_manager.driver
            self.page_validator = PageValidator(self.driver)
            print(f"[{get_timestamp()}] Browser setup successful for purchase workflow")
        
        return success
    
    def cleanup_browser(self):
        """Clean up browser resources."""
        if self.webdriver_manager:
            self.webdriver_manager.quit_driver()
            print(f"[{get_timestamp()}] Browser resources cleaned up")
    
    def execute_purchase_workflow(self, available_products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main workflow function to execute purchases for available products.
        
        Args:
            available_products: List of product dictionaries from scraper.py
            
        Returns:
            Dictionary containing purchase attempt results and summary
        """
        print(f"[{get_timestamp()}] Starting purchase workflow for {len(available_products)} products")
        
        # Setup browser
        if not self.setup_browser():
            return {
                'success': False,
                'error': 'Failed to setup browser',
                'purchase_attempts': [],
                'summary': {'total_products': len(available_products), 'purchase_attempts': 0, 'successful_purchases': 0}
            }
        
        purchase_results = []
        
        try:
            for product in available_products:
                product_url = product.get('url')
                product_name = product.get('name', product.get('title', 'Unknown Product'))
                
                if product_url:
                    print(f"[{get_timestamp()}] Attempting to purchase: {product_name}")
                    success, message = self._attempt_purchase(product_url, product_name)
                    
                    purchase_result = {
                        'product': product_name,
                        'url': product_url,
                        'purchase_success': success,
                        'purchase_message': message,
                        'timestamp': get_timestamp()
                    }
                    purchase_results.append(purchase_result)
                    
                    if success:
                        print(f"[{get_timestamp()}] Successfully initiated purchase for: {product_name}")
                    else:
                        print(f"[{get_timestamp()}] Failed to purchase {product_name}: {message}")
                else:
                    print(f"[{get_timestamp()}] No URL available for product: {product_name}")
        
        finally:
            # Always cleanup browser resources
            self.cleanup_browser()
        
        # Generate summary
        successful_purchases = sum(1 for r in purchase_results if r.get('purchase_success', False))
        
        results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'purchase_attempts': purchase_results,
            'summary': {
                'total_products': len(available_products),
                'purchase_attempts': len(purchase_results),
                'successful_purchases': successful_purchases,
                'failed_purchases': len(purchase_results) - successful_purchases
            }
        }
        
        # Print summary
        print(f"\n[{get_timestamp()}] PURCHASE WORKFLOW SUMMARY:")
        print(f"  Total products available: {len(available_products)}")
        print(f"  Purchase attempts made: {len(purchase_results)}")
        print(f"  Successful purchases: {successful_purchases}")
        print(f"  Failed purchases: {len(purchase_results) - successful_purchases}")
        
        return results
    
    def _attempt_purchase(self, product_url: str, product_name: str) -> Tuple[bool, str]:
        """
        Attempt to purchase a single product.
        
        Args:
            product_url: URL of the product page
            product_name: Name of the product for logging
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Normalize and validate URL
            normalized_url = self._normalize_product_url(product_url)
            if not self._is_valid_url(normalized_url):
                return False, "Invalid URL"

            print(f"[{get_timestamp()}] Navigating to product page: {normalized_url}")
            self.driver.get(normalized_url)

            # Take screenshot before attempting purchase
            if self.webdriver_manager:
                self.webdriver_manager.take_screenshot("before_purchase", normalized_url)

            # Wait for page to load
            if not self.page_validator.wait_for_page_ready(normalized_url):
                print(f"[{get_timestamp()}] Page failed to load for purchase: {normalized_url}")
                return False, "Page failed to load"

            # Find and click buy now button
            buy_button = self._find_buy_now_button()
            if not buy_button:
                print(f"[{get_timestamp()}] No buy now button found on page: {normalized_url}")
                return False, "No buy now button found"

            # Click the button
            print(f"[{get_timestamp()}] Clicking buy now button for {product_name}...")
            buy_button.click()
            
            # Take screenshot after clicking buy button
            if self.webdriver_manager:
                self.webdriver_manager.take_screenshot("after_purchase_click", normalized_url)

            print(f"[{get_timestamp()}] Successfully clicked buy now button for: {product_name}")
            return True, "Buy now button clicked successfully"

        except Exception as e:
            error_msg = f"Error during purchase attempt: {str(e)}"
            print(f"[{get_timestamp()}] {error_msg}")
            return False, error_msg
    
    def _normalize_product_url(self, product_url: str) -> str:
        """Normalize product URL to absolute format."""
        return normalize_url(product_url)
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for processing."""
        return url and url.startswith('http')
    
    def _find_buy_now_button(self):
        """Find the buy now button using various selectors."""
        if not SELENIUM_AVAILABLE:
            return None
            
        # Try CSS selectors first
        for selector in BUY_NOW_SELECTORS:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Return the first visible and enabled element
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            print(f"[{get_timestamp()}] Found buy button with selector: {selector}")
                            return element
            except (NoSuchElementException, Exception):
                continue
        
        # Try searching by text content as fallback
        try:
            # Look for buttons with "buy now" text (case insensitive)
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                button_text = (button.text or "").lower()
                if any(phrase in button_text for phrase in ["buy now", "add to cart", "purchase"]):
                    if button.is_displayed() and button.is_enabled():
                        print(f"[{get_timestamp()}] Found buy button by text: {button.text}")
                        return button
        except Exception as e:
            print(f"[{get_timestamp()}] Error searching for button by text: {str(e)}")
        
        return None


def trigger_purchase_workflow(available_products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main entry point function to trigger the purchase workflow.
    
    This function can be called from scraper.py when available products are detected.
    
    Args:
        available_products: List of available product dictionaries from scraper.py
        
    Returns:
        Dictionary containing purchase results and summary
    """
    print(f"[{get_timestamp()}] Purchase workflow triggered with {len(available_products)} available products")
    
    if not available_products:
        return {
            'success': True,
            'message': 'No products to purchase',
            'purchase_attempts': [],
            'summary': {'total_products': 0, 'purchase_attempts': 0, 'successful_purchases': 0}
        }
    
    workflow = PurchaseWorkflow()
    results = workflow.execute_purchase_workflow(available_products)
    
    # Save results to JSON file
    try:
        filename = f"purchase_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"[{get_timestamp()}] Purchase workflow results saved to {filename}")
    except Exception as e:
        print(f"[{get_timestamp()}] Error saving purchase results: {str(e)}")
    
    return results


if __name__ == "__main__":
    # Example usage / testing
    print("Purchase Workflow Module")
    print("This module is designed to be imported and used by scraper.py")
    print("Example usage:")
    print("  from purchase_workflow import trigger_purchase_workflow")
    print("  results = trigger_purchase_workflow(available_products)")