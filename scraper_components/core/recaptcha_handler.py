#!/usr/bin/env python3
"""
reCAPTCHA handling component for managing CAPTCHA challenges.

Handles detection and interaction with reCAPTCHA and other CAPTCHA systems.
"""

import time
from typing import Optional, Tuple

from ..config.constants import RECAPTCHA_INDICATORS, RECAPTCHA_SELECTORS
from ..utils.helpers import get_timestamp

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    class By:
        CSS_SELECTOR = "css selector"
        XPATH = "xpath"
    class WebDriverWait:
        def __init__(self, driver, timeout): pass
        def until(self, condition): pass
    class TimeoutException(Exception):
        pass
    class NoSuchElementException(Exception):
        pass
    class ElementClickInterceptedException(Exception):
        pass


class ReCAPTCHAHandler:
    """Handles reCAPTCHA detection and interaction."""
    
    def __init__(self, driver, webdriver_manager=None):
        self.driver = driver
        self.webdriver_manager = webdriver_manager
    
    def detect_recaptcha(self) -> bool:
        """
        Detect if current page contains a reCAPTCHA challenge.
        Returns True if reCAPTCHA is detected.
        """
        try:
            page_source = (self.driver.page_source or "").lower()
            page_title = (self.driver.title or "").lower()
            
            # Check for text indicators in page content
            for indicator in RECAPTCHA_INDICATORS:
                if indicator in page_source or indicator in page_title:
                    print(f"[{get_timestamp()}] reCAPTCHA detected: Found indicator '{indicator}'")
                    return True
            
            # Check for reCAPTCHA elements using selectors
            for selector in RECAPTCHA_SELECTORS:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"[{get_timestamp()}] reCAPTCHA detected: Found element with selector '{selector}'")
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error detecting reCAPTCHA: {str(e)}")
            return False
    
    def handle_recaptcha(self, timeout: int = 30) -> bool:
        """
        Attempt to handle reCAPTCHA challenge by clicking the checkbox.
        Returns True if successfully handled, False otherwise.
        """
        try:
            print(f"[{get_timestamp()}] Attempting to handle reCAPTCHA...")
            
            # Take screenshot before attempting to handle reCAPTCHA
            if self.webdriver_manager:
                self.webdriver_manager.take_screenshot("recaptcha_detected", self.driver.current_url)
            
            # Look for reCAPTCHA iframe and switch to it
            recaptcha_element = self._find_recaptcha_element()
            if not recaptcha_element:
                print(f"[{get_timestamp()}] Could not find reCAPTCHA element to interact with")
                return False
            
            # Attempt to click the reCAPTCHA checkbox
            success = self._click_recaptcha_checkbox(recaptcha_element, timeout)
            
            if success:
                print(f"[{get_timestamp()}] reCAPTCHA handling completed successfully")
                # Take screenshot after successful handling
                if self.webdriver_manager:
                    self.webdriver_manager.take_screenshot("recaptcha_completed", self.driver.current_url)
                return True
            else:
                print(f"[{get_timestamp()}] reCAPTCHA handling failed")
                return False
                
        except Exception as e:
            print(f"[{get_timestamp()}] Error handling reCAPTCHA: {str(e)}")
            return False
    
    def _find_recaptcha_element(self) -> Optional[object]:
        """Find the reCAPTCHA element to interact with."""
        try:
            # Try different strategies to find reCAPTCHA elements
            
            # Strategy 1: Look for reCAPTCHA iframe
            try:
                iframe = self.driver.find_element(By.CSS_SELECTOR, 'iframe[src*="recaptcha"]')
                if iframe:
                    print(f"[{get_timestamp()}] Found reCAPTCHA iframe")
                    return iframe
            except NoSuchElementException:
                pass
            
            # Strategy 2: Look for direct reCAPTCHA checkbox elements
            for selector in RECAPTCHA_SELECTORS:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"[{get_timestamp()}] Found reCAPTCHA element with selector: {selector}")
                        return elements[0]
                except Exception:
                    continue
            
            # Strategy 3: Look for common reCAPTCHA patterns with XPath
            xpath_selectors = [
                "//div[contains(@class, 'recaptcha')]",
                "//div[contains(text(), 'not a robot')]",
                "//span[contains(text(), 'not a robot')]",
                "//div[@role='checkbox']",
                "//input[@type='checkbox' and contains(@aria-label, 'not a robot')]"
            ]
            
            for xpath in xpath_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    if element and element.is_displayed():
                        print(f"[{get_timestamp()}] Found reCAPTCHA element with XPath: {xpath}")
                        return element
                except NoSuchElementException:
                    continue
            
            return None
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error finding reCAPTCHA element: {str(e)}")
            return None
    
    def _click_recaptcha_checkbox(self, element, timeout: int = 30) -> bool:
        """Click the reCAPTCHA checkbox element."""
        try:
            # If it's an iframe, switch to it first
            if element.tag_name == 'iframe':
                print(f"[{get_timestamp()}] Switching to reCAPTCHA iframe...")
                self.driver.switch_to.frame(element)
                
                # Look for the checkbox inside the iframe
                wait = WebDriverWait(self.driver, 10)
                try:
                    checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.recaptcha-checkbox-border')))
                    print(f"[{get_timestamp()}] Found reCAPTCHA checkbox in iframe")
                except TimeoutException:
                    # Try alternative selectors
                    try:
                        checkbox = self.driver.find_element(By.CSS_SELECTOR, '#recaptcha-anchor')
                    except NoSuchElementException:
                        checkbox = self.driver.find_element(By.CSS_SELECTOR, 'div[role="checkbox"]')
                
                element = checkbox
            
            # Wait for element to be clickable
            wait = WebDriverWait(self.driver, timeout)
            clickable_element = wait.until(EC.element_to_be_clickable(element))
            
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", clickable_element)
            time.sleep(1)  # Brief pause for scroll
            
            # Attempt to click
            print(f"[{get_timestamp()}] Clicking reCAPTCHA checkbox...")
            try:
                clickable_element.click()
            except ElementClickInterceptedException:
                # Try JavaScript click if regular click fails
                self.driver.execute_script("arguments[0].click();", clickable_element)
            
            # Wait a moment for reCAPTCHA to process
            time.sleep(3)
            
            # Switch back to main frame if we were in an iframe
            self.driver.switch_to.default_content()
            
            # Wait for potential page redirect or change
            time.sleep(5)
            
            return True
            
        except TimeoutException:
            print(f"[{get_timestamp()}] Timeout waiting for reCAPTCHA element to be clickable")
            self.driver.switch_to.default_content()  # Ensure we're back to main frame
            return False
        except Exception as e:
            print(f"[{get_timestamp()}] Error clicking reCAPTCHA checkbox: {str(e)}")
            self.driver.switch_to.default_content()  # Ensure we're back to main frame
            return False
    
    def wait_for_recaptcha_completion(self, timeout: int = 60) -> bool:
        """
        Wait for reCAPTCHA to be completed and page to proceed.
        Returns True if page changes/proceeds, False if timeout.
        """
        try:
            print(f"[{get_timestamp()}] Waiting for reCAPTCHA completion...")
            
            start_url = self.driver.current_url
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Check if URL has changed (indicating redirect)
                current_url = self.driver.current_url
                if current_url != start_url:
                    print(f"[{get_timestamp()}] URL changed from {start_url} to {current_url}")
                    return True
                
                # Check if reCAPTCHA is no longer present
                if not self.detect_recaptcha():
                    print(f"[{get_timestamp()}] reCAPTCHA no longer detected on page")
                    return True
                
                time.sleep(2)  # Check every 2 seconds
            
            print(f"[{get_timestamp()}] Timeout waiting for reCAPTCHA completion")
            return False
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error waiting for reCAPTCHA completion: {str(e)}")
            return False