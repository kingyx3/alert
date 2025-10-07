#!/usr/bin/env python3
"""
WebDriver management component for browser automation.

Handles Chrome driver setup, configuration, and lifecycle management.
"""

import os
from datetime import datetime
from typing import Optional

from ..config.constants import DEFAULT_WINDOW_SIZE, SYSTEM_CHROMEDRIVER_PATH
from ..utils.helpers import get_timestamp

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    # Create mock classes to prevent import errors
    class Options:
        def add_argument(self, arg): pass
    class Service:
        def __init__(self, path): pass
    webdriver = None

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class WebDriverManager:
    """Manages Chrome WebDriver setup and configuration."""
    
    def __init__(self):
        self.driver = None
    
    def setup_driver(self) -> bool:
        """Setup Chrome driver with recommended options and return success state."""
        if not SELENIUM_AVAILABLE:
            print(f"[{get_timestamp()}] Selenium is not installed/available.")
            return False

        chrome_options = self._get_chrome_options()
        
        # Try system chromedriver first, then webdriver-manager fallback
        if self._try_system_chromedriver(chrome_options):
            return True
        elif self._try_webdriver_manager(chrome_options):
            return True
        else:
            return False
    
    def _get_chrome_options(self) -> Options:
        """Configure Chrome options for headless scraping."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'--window-size={DEFAULT_WINDOW_SIZE}')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        return chrome_options
    
    def _try_system_chromedriver(self, chrome_options: Options) -> bool:
        """Try to setup driver with system chromedriver."""
        if not SELENIUM_AVAILABLE:
            return False
        
        try:
            service = Service(SYSTEM_CHROMEDRIVER_PATH)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return True
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to setup Chrome driver with system chromedriver: {str(e)}")
            return False
    
    def _try_webdriver_manager(self, chrome_options: Options) -> bool:
        """Try to setup driver with webdriver-manager."""
        if not SELENIUM_AVAILABLE or not WEBDRIVER_MANAGER_AVAILABLE:
            print(f"[{get_timestamp()}] WebDriver manager not available")
            return False
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return True
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to setup Chrome driver with webdriver manager: {str(e)}")
            return False
    
    def take_screenshot(self, page_type: str = "page", url: str = "") -> Optional[str]:
        """
        Take a screenshot of the current page and save it to screenshots directory.
        Returns the filename if successful, None otherwise.
        """
        if not self.driver:
            print(f"[{get_timestamp()}] Cannot take screenshot: No driver available")
            return None
        
        try:
            # Create screenshots directory if it doesn't exist
            screenshots_dir = "screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Generate filename with timestamp and page type
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            safe_page_type = page_type.replace(" ", "_").replace("/", "_")
            
            # Extract domain from URL for context
            domain_part = ""
            if url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain_part = f"_{parsed.netloc.replace('.', '_')}"
                except:
                    pass
            
            filename = f"{safe_page_type}{domain_part}_{timestamp}.png"
            filepath = os.path.join(screenshots_dir, filename)
            
            # Take screenshot
            self.driver.save_screenshot(filepath)
            print(f"[{get_timestamp()}] Screenshot saved: {filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to take screenshot: {str(e)}")
            return None

    def quit_driver(self) -> None:
        """Safely quit the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None