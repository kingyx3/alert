#!/usr/bin/env python3
"""
Product extraction component for parsing product information from web elements.

Handles product discovery, information extraction, and data structuring.
"""

from typing import List, Optional, Dict, Any

from ..config.constants import (
    PRODUCT_SELECTORS, PRICE_SELECTORS, TITLE_SELECTORS, PRICE_EXTRACT_SELECTORS
)
from ..models.product import Product
from ..utils.helpers import get_timestamp, safe_get_attribute, is_valid_price_text

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    class By:
        CSS_SELECTOR = "css selector"
        XPATH = "xpath"
    class WebDriverWait:
        def __init__(self, driver, timeout): pass
        def until(self, condition): pass
    class EC:
        @staticmethod
        def presence_of_all_elements_located(locator): pass
    class TimeoutException(Exception):
        pass
    class NoSuchElementException(Exception):
        pass


class ProductExtractor:
    """Extracts product information from web pages."""
    
    def __init__(self, driver):
        self.driver = driver
    
    def wait_for_products_to_load(self, timeout: int = 20) -> List[Any]:
        """
        Wait for known product selectors; fallback to price selectors and extract parent containers.
        Returns a list of selenium web elements (product containers) or empty list.
        """
        try:
            # Try primary product selectors first
            elements = self._try_product_selectors(timeout)
            if elements:
                return elements
            
            # Fallback to price-based extraction
            elements = self._try_price_selector_fallback(timeout)
            if elements:
                return elements
                
            print(f"[{get_timestamp()}] No products found with known selectors within {timeout} seconds")
            return []
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error waiting for products: {str(e)}")
            return []
    
    def _try_product_selectors(self, timeout: int) -> List[Any]:
        """Try primary product selectors."""
        for selector in PRODUCT_SELECTORS:
            try:
                wait = WebDriverWait(self.driver, timeout)
                elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                if elements:
                    print(f"[{get_timestamp()}] Found {len(elements)} products using selector: {selector}")
                    return elements
            except TimeoutException:
                continue
        return []
    
    def _try_price_selector_fallback(self, timeout: int) -> List[Any]:
        """Fallback: wait for price elements and use their parent containers."""
        for selector in PRICE_SELECTORS:
            try:
                wait = WebDriverWait(self.driver, timeout)
                elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                if elements:
                    print(f"[{get_timestamp()}] Found {len(elements)} price elements, extracting parent containers")
                    product_containers = []
                    for elem in elements:
                        try:
                            parent = elem.find_element(By.XPATH, "./../..")
                            if parent not in product_containers:
                                product_containers.append(parent)
                        except Exception:
                            continue
                    return product_containers[:20]
            except TimeoutException:
                continue
        return []
    
    def extract_product_info_from_element(self, element) -> Optional[Product]:
        """Extract title, image and url from a product container element."""
        try:
            title = self._extract_title(element)
            image_url = self._extract_image_url(element)
            product_url = self._extract_product_url(element)
            
            if title:
                return Product(
                    title=title or 'No title available',
                    image=image_url,
                    url=product_url
                )
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error extracting product info: {str(e)}")
        
        return None
    
    def _extract_title(self, element) -> str:
        """Extract product title from element."""
        for selector in TITLE_SELECTORS:
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, selector)
                title = safe_get_attribute(title_elem, 'title') or (title_elem.text or "").strip()
                if title:
                    return title
            except NoSuchElementException:
                continue
        return ""
    
    def _extract_image_url(self, element) -> str:
        """Extract product image URL from element."""
        try:
            img_elem = element.find_element(By.CSS_SELECTOR, 'img')
            return (safe_get_attribute(img_elem, 'src') or 
                   safe_get_attribute(img_elem, 'data-src') or "")
        except NoSuchElementException:
            return ""
    
    def _extract_product_url(self, element) -> str:
        """Extract product URL from element."""
        try:
            link_elem = element.find_element(By.CSS_SELECTOR, 'a')
            return safe_get_attribute(link_elem, 'href') or ""
        except NoSuchElementException:
            return ""
    
    def extract_price_from_page(self) -> Optional[str]:
        """Try many selectors and return first reasonable price-like string found."""
        try:
            for selector in PRICE_EXTRACT_SELECTORS:
                try:
                    price_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in price_elements:
                        price_text = (elem.text or "").strip()
                        if price_text and is_valid_price_text(price_text):
                            price_text = price_text.replace('\n', ' ').strip()
                            if len(price_text) < 50:
                                print(f"[{get_timestamp()}] Found price: {price_text}")
                                return price_text
                except (NoSuchElementException, Exception):
                    continue
            
            print(f"[{get_timestamp()}] No price found on page")
            return None
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error extracting price: {str(e)}")
            return None