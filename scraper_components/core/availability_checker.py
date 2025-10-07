#!/usr/bin/env python3
"""
Availability checker component for determining product availability.

Handles availability detection, quantity checking, and product status validation.
"""

from typing import Tuple, Optional

from ..config.constants import BUY_INDICATORS, QUANTITY_SELECTORS
from ..utils.helpers import get_timestamp, safe_get_attribute, normalize_url

try:
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    class By:
        CSS_SELECTOR = "css selector"
    class NoSuchElementException(Exception):
        pass


class AvailabilityChecker:
    """Checks product availability on individual product pages."""
    
    def __init__(self, driver, page_validator, product_extractor=None, webdriver_manager=None):
        self.driver = driver
        self.page_validator = page_validator
        self.product_extractor = product_extractor
        self.webdriver_manager = webdriver_manager
    
    def check_product_availability(self, product_url: str) -> Tuple[bool, str, Optional[str]]:
        """
        Visit product_url, validate page loaded, attempt price extraction and availability check.
        Returns (is_available, status_string, price_or_None)
        """
        try:
            # Normalize and validate URL
            normalized_url = self._normalize_product_url(product_url)
            if not self._is_valid_url(normalized_url):
                return False, "Invalid URL", None

            print(f"[{get_timestamp()}] Checking availability and price for: {normalized_url}")
            self.driver.get(normalized_url)

            # Take screenshot of individual product page (before validation to capture even failed pages)
            if self.webdriver_manager:
                print(f"[{get_timestamp()}] Taking screenshot of product page...")
                self.webdriver_manager.take_screenshot("product_page", normalized_url)

            # Wait for page to load and validate content
            if not self.page_validator.wait_for_page_ready(normalized_url):
                print(f"[{get_timestamp()}] Page failed to load correctly for: {normalized_url}")
                # Take additional screenshot for failed page validation with different label
                if self.webdriver_manager:
                    print(f"[{get_timestamp()}] Taking screenshot of failed page load...")
                    self.webdriver_manager.take_screenshot("product_page_failed", normalized_url)
                return False, "Page failed to load correctly", None

            # Extract price and check availability
            price = self._extract_price_from_page()
            is_available, availability_reason = self.check_availability_indicators()

            if is_available:
                status = f"Available{' - ' + price if price else ''}"
                return True, status, price
            else:
                print(f"Product not available: {normalized_url} ({availability_reason})")
                return False, f"Not available ({availability_reason})", price

        except Exception as e:
            print(f"[{get_timestamp()}] Error checking product availability: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    def _normalize_product_url(self, product_url: str) -> str:
        """Normalize product URL to absolute format."""
        return normalize_url(product_url)
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for processing."""
        return url and url.startswith('http')
    
    def check_availability_indicators(self) -> Tuple[bool, str]:
        """Check presence of buy/add-to-cart style indicators in the page source."""
        try:
            page_source = (self.driver.page_source or "").lower()
            has_buy_indicators = any(indicator in page_source for indicator in BUY_INDICATORS)
            
            if has_buy_indicators:
                return True, "Buy/Add to cart options available"
            else:
                return False, "No buy options found"
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error checking availability indicators: {str(e)}")
            return False, f"Error checking indicators: {str(e)}"

    def check_quantity_selector_disabled(self) -> bool:
        """Check if any quantity inputs are disabled/read-only."""
        try:
            for selector in QUANTITY_SELECTORS:
                try:
                    quantity_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in quantity_elements:
                        if self._is_quantity_disabled(elem):
                            print(f"[{get_timestamp()}] Found disabled quantity selector")
                            return True
                except (NoSuchElementException, Exception):
                    continue
            return False
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error checking quantity selector: {str(e)}")
            return False
    
    def _is_quantity_disabled(self, element) -> bool:
        """Check if a quantity element is disabled."""
        try:
            class_attr = (element.get_attribute('class') or "").lower()
            return (
                element.get_attribute('disabled') is not None or
                element.get_attribute('readonly') is not None or
                ('disabled' in class_attr if class_attr else False)
            )
        except Exception:
            return False
    
    def _extract_price_from_page(self) -> Optional[str]:
        """Extract price from current page using ProductExtractor if available."""
        if self.product_extractor:
            return self.product_extractor.extract_price_from_page()
        return None