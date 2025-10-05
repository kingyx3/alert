#!/usr/bin/env python3
"""
Page validation component for ensuring proper page loading.

Handles page readiness checks, content validation, and error detection.
"""

import time
from typing import Optional

from ..config.constants import CRITICAL_ERROR_INDICATORS, PRODUCT_PAGE_INDICATORS
from ..utils.helpers import get_timestamp
from .recaptcha_handler import ReCAPTCHAHandler

try:
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    class WebDriverWait:
        def __init__(self, driver, timeout): pass
        def until(self, condition): pass
    class TimeoutException(Exception):
        pass


class PageValidator:
    """Validates page loading and content for scraping operations."""
    
    def __init__(self, driver, webdriver_manager=None):
        self.driver = driver
        self.webdriver_manager = webdriver_manager
        self.recaptcha_handler = ReCAPTCHAHandler(driver, webdriver_manager)
    
    def wait_for_page_ready(self, expected_url: Optional[str] = None, timeout: int = 10) -> bool:
        """Wait for document readyState == 'complete' and ensure content stability."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Wait for content to stabilize - check that page source doesn't change
            print(f"[{get_timestamp()}] Waiting for page content to stabilize...")
            stable_attempts = 0
            max_stability_checks = 3
            stability_wait = 2  # seconds between checks
            
            previous_source_length = 0
            for attempt in range(max_stability_checks):
                time.sleep(stability_wait)
                current_source_length = len(self.driver.page_source or "")
                
                if current_source_length == previous_source_length and current_source_length > 0:
                    stable_attempts += 1
                    if stable_attempts >= 2:  # Need 2 consecutive stable checks
                        print(f"[{get_timestamp()}] Page content stabilized after {(attempt + 1) * stability_wait} seconds")
                        break
                else:
                    stable_attempts = 0
                    previous_source_length = current_source_length
            else:
                print(f"[{get_timestamp()}] Page content may not be fully stable, proceeding anyway")
            
            if expected_url:
                return self.validate_page_loaded(expected_url)
            return True
            
        except TimeoutException:
            print(f"[{get_timestamp()}] Timeout waiting for page to be ready")
            return False
        except Exception as e:
            print(f"[{get_timestamp()}] Error waiting for page ready: {str(e)}")
            return False

    def validate_page_loaded(self, expected_url: Optional[str]) -> bool:
        """Validate that the current page contains meaningful product-related content."""
        try:
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            if not self._is_valid_url(current_url):
                return False
                
            if not self._has_sufficient_content(page_source):
                return False
                
            # Check for reCAPTCHA and handle it if present
            if self.recaptcha_handler.detect_recaptcha():
                print(f"[{get_timestamp()}] reCAPTCHA detected, attempting to handle...")
                
                if self.recaptcha_handler.handle_recaptcha():
                    # Wait for reCAPTCHA completion and page to proceed
                    if self.recaptcha_handler.wait_for_recaptcha_completion():
                        print(f"[{get_timestamp()}] reCAPTCHA handled successfully, re-validating page...")
                        # Re-get page source after reCAPTCHA handling
                        page_source = self.driver.page_source
                        current_url = self.driver.current_url
                    else:
                        print(f"[{get_timestamp()}] reCAPTCHA completion timeout")
                        return False
                else:
                    print(f"[{get_timestamp()}] Failed to handle reCAPTCHA")
                    return False
                
            page_lower = page_source.lower()
            
            if self._has_critical_errors(page_lower):
                return False
                
            if self._has_ambiguous_errors(page_lower):
                return False
                
            if not self._has_product_indicators(page_lower, expected_url, page_source):
                return False
                
            print(f"[{get_timestamp()}] Page validation passed for: {expected_url}")
            return True
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error validating page load: {str(e)}")
            return False
    
    def _is_valid_url(self, current_url: str) -> bool:
        """Check if current URL is valid."""
        if not current_url or current_url == "data:,":
            print(f"[{get_timestamp()}] Page validation failed: Invalid current URL: {current_url}")
            return False
        return True
    
    def _has_sufficient_content(self, page_source: str) -> bool:
        """Check if page has sufficient content."""
        if not page_source or len(page_source.strip()) < 50:
            print(f"[{get_timestamp()}] Page validation failed: Page content too short or empty")
            return False
        return True
    
    def _has_critical_errors(self, page_lower: str) -> bool:
        """Check for critical error indicators."""
        found_critical = [i for i in CRITICAL_ERROR_INDICATORS if i in page_lower]
        if found_critical:
            print(f"[{get_timestamp()}] Page validation failed: Error page detected - {found_critical}")
            return True
        return False
    
    def _has_ambiguous_errors(self, page_lower: str) -> bool:
        """Check for ambiguous error phrases."""
        title_lower = (self.driver.title or "").lower()
        ambiguous_error_phrases = ['error occurred', 'something went wrong', 'try again later']
        
        for phrase in ambiguous_error_phrases:
            if phrase in title_lower:
                print(f"[{get_timestamp()}] Page validation failed: Error phrase in title - '{phrase}'")
                return True
            
            # look for phrase in obvious error markup contexts
            contexts = [
                f'<h1>{phrase}</h1>', f'<h2>{phrase}</h2>', f'<h3>{phrase}</h3>',
                f'<div class="error">{phrase}', f'<div class="message">{phrase}',
                f'<p class="error">{phrase}', f'<span class="error">{phrase}'
            ]
            if any(context in page_lower for context in contexts):
                print(f"[{get_timestamp()}] Page validation failed: Error message in error context - '{phrase}'")
                return True
        
        return False
    
    def _has_product_indicators(self, page_lower: str, expected_url: Optional[str], page_source: str) -> bool:
        """Check for product-related content indicators."""
        found_indicators = [ind for ind in PRODUCT_PAGE_INDICATORS if ind in page_lower]
        if not found_indicators:
            print(f"[{get_timestamp()}] Page validation failed: No product-related content found")
            print(f"[{get_timestamp()}] Page title: {self.driver.title}")
            print(f"[{get_timestamp()}] Page source length: {len(page_source)}")
            sample_content = page_source[:500] if len(page_source) > 500 else page_source
            print(f"[{get_timestamp()}] Page content sample: {sample_content[:200]}...")
            return False
        
        print(f"[{get_timestamp()}] Found indicators: {found_indicators[:5]}...")
        return True