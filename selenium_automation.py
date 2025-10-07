#!/usr/bin/env python3

"""
Selenium Automation Module
Automates browser interactions to click "buy now" buttons when items are available
Includes debugging screenshot functionality
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Selenium imports with fallback
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available. Please install selenium package.")
    # Mock classes for type hints when selenium is not available
    class webdriver:
        class Chrome:
            pass

# Constants
DEFAULT_TIMEOUT = 15  # Reduced from 30s for faster operations
SCREENSHOT_DIR = "screenshots"
# Human-like timing ranges (in seconds) - optimized for speed while maintaining naturalness
HUMAN_MIN_DELAY = 0.3
HUMAN_MAX_DELAY = 1.2
PAGE_LOAD_MIN_DELAY = 0.5
PAGE_LOAD_MAX_DELAY = 2.0
BETWEEN_PRODUCTS_MIN_DELAY = 0.8
BETWEEN_PRODUCTS_MAX_DELAY = 1.8

# Global driver instance for reuse (significantly faster than creating new driver each time)
_global_driver = None
BUY_BUTTON_SELECTORS = [
    "button[data-spm-click*='buy']",
    "button:contains('Buy Now')",
    "button:contains('Add to Cart')",
    ".add-to-cart-btn",
    ".buy-now-btn", 
    "[data-testid='buy-button']",
    ".pdp-button-colour--orange",  # Lazada specific
    ".add-to-cart",
    "button[aria-label*='buy']"
]

def get_timestamp() -> str:
    """Return current timestamp for file naming."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def human_delay(min_delay: float = HUMAN_MIN_DELAY, max_delay: float = HUMAN_MAX_DELAY) -> None:
    """
    Introduce human-like random delays to avoid bot detection.
    
    Args:
        min_delay (float): Minimum delay in seconds
        max_delay (float): Maximum delay in seconds
    """
    import random
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)

def setup_chrome_driver(headless: bool = True) -> Optional[webdriver.Chrome]:
    """
    Set up Chrome WebDriver optimized for speed and human-like behavior.
    
    Args:
        headless (bool): Whether to run in headless mode
        
    Returns:
        webdriver.Chrome: Configured Chrome driver or None if setup fails
    """
    if not SELENIUM_AVAILABLE:
        print(f"[{datetime.now()}] Selenium not available - cannot create webdriver")
        return None
        
    try:
        options = ChromeOptions()
        
        if headless:
            options.add_argument('--headless=new')  # Use new headless mode for better performance
        
        # Performance optimizations for faster startup
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # Bot detection avoidance - more human-like browser
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Realistic user agent - randomly choose from common ones
        import random
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # Realistic window size - vary slightly
        width = random.randint(1366, 1920)
        height = random.randint(768, 1080)
        options.add_argument(f'--window-size={width},{height}')
        
        # Enhanced preferences for human-like behavior
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2  # Don't load images for faster page loads
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        # Faster page loading
        options.add_argument('--aggressive-cache-discard')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        
        # Try to create driver with faster timeout
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(DEFAULT_TIMEOUT)
        
        # Execute script to hide webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"[{datetime.now()}] Chrome WebDriver initialized successfully")
        return driver
        
    except Exception as e:
        print(f"[{datetime.now()}] Failed to initialize Chrome WebDriver: {str(e)}")
        return None

def get_or_create_driver(headless: bool = True, force_new: bool = False) -> Optional[webdriver.Chrome]:
    """
    Get existing driver or create new one for better performance.
    
    Args:
        headless (bool): Whether to run in headless mode
        force_new (bool): Force creation of new driver
        
    Returns:
        webdriver.Chrome: WebDriver instance or None if setup fails
    """
    global _global_driver
    
    # Check if we can reuse existing driver
    if not force_new and _global_driver is not None:
        try:
            # Test if driver is still alive
            _global_driver.current_url
            print(f"[{datetime.now()}] Reusing existing WebDriver for better performance")
            return _global_driver
        except Exception:
            # Driver is dead, need to create new one
            _global_driver = None
    
    # Create new driver
    _global_driver = setup_chrome_driver(headless)
    return _global_driver

def cleanup_driver() -> None:
    """Clean up the global driver instance."""
    global _global_driver
    if _global_driver is not None:
        try:
            _global_driver.quit()
            print(f"[{datetime.now()}] Global WebDriver cleaned up successfully")
        except Exception as e:
            print(f"[{datetime.now()}] Error cleaning up WebDriver: {str(e)}")
        finally:
            _global_driver = None

def ensure_screenshot_dir() -> str:
    """
    Ensure screenshot directory exists and return its path.
    
    Returns:
        str: Path to screenshot directory
    """
    Path(SCREENSHOT_DIR).mkdir(exist_ok=True)
    return SCREENSHOT_DIR

def take_debug_screenshot(driver: webdriver.Chrome, filename: str, description: str = "") -> bool:
    """
    Take a screenshot for debugging purposes.
    
    Args:
        driver (webdriver.Chrome): WebDriver instance
        filename (str): Filename for the screenshot
        description (str): Description of what the screenshot shows
        
    Returns:
        bool: True if screenshot was taken successfully
    """
    try:
        screenshot_dir = ensure_screenshot_dir()
        full_path = os.path.join(screenshot_dir, filename)
        
        success = driver.save_screenshot(full_path)
        if success:
            print(f"[{datetime.now()}] Screenshot saved: {full_path}")
            if description:
                print(f"[{datetime.now()}] Screenshot description: {description}")
        else:
            print(f"[{datetime.now()}] Failed to save screenshot: {full_path}")
            
        return success
        
    except Exception as e:
        print(f"[{datetime.now()}] Error taking screenshot {filename}: {str(e)}")
        return False

def find_buy_button(driver: webdriver.Chrome) -> Optional[Any]:
    """
    Find a buy button using various selectors.
    
    Args:
        driver (webdriver.Chrome): WebDriver instance
        
    Returns:
        WebElement or None: Found buy button element
    """
    for selector in BUY_BUTTON_SELECTORS:
        try:
            # Try CSS selector first
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                # Return first visible and enabled element
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"[{datetime.now()}] Found buy button with selector: {selector}")
                        return element
        except Exception as e:
            print(f"[{datetime.now()}] Error with selector {selector}: {str(e)}")
            continue
    
    # Try additional text-based search
    try:
        buy_texts = ["Buy Now", "Add to Cart", "BUY NOW", "ADD TO CART", "立即购买", "加入购物车"]
        for text in buy_texts:
            elements = driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
            if elements:
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"[{datetime.now()}] Found buy button with text: {text}")
                        return element
    except Exception as e:
        print(f"[{datetime.now()}] Error in text-based search: {str(e)}")
    
    print(f"[{datetime.now()}] No buy button found on page")
    return None

def attempt_purchase(driver: webdriver.Chrome, product_url: str, product_name: str, debug_screenshots: bool = True) -> bool:
    """
    Attempt to purchase a product by clicking the buy button.
    
    Args:
        driver (webdriver.Chrome): WebDriver instance
        product_url (str): URL of the product page
        product_name (str): Name of the product for logging
        debug_screenshots (bool): Whether to take debug screenshots
        
    Returns:
        bool: True if purchase attempt was successful
    """
    timestamp = get_timestamp()
    
    try:
        print(f"[{datetime.now()}] Attempting to purchase: {product_name}")
        print(f"[{datetime.now()}] Navigating to: {product_url}")
        
        # Navigate to product page
        driver.get(product_url)
        
        # Take initial screenshot only if debug enabled
        if debug_screenshots:
            take_debug_screenshot(
                driver, 
                f"product_page_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
                f"Initial product page for {product_name}"
            )
        
        # Wait for page to load with shorter timeout
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Human-like wait for dynamic content
        human_delay(PAGE_LOAD_MIN_DELAY, PAGE_LOAD_MAX_DELAY)
        
        # Look for buy button
        buy_button = find_buy_button(driver)
        
        if not buy_button:
            # Always take screenshot on failure for debugging
            take_debug_screenshot(
                driver,
                f"no_buy_button_{timestamp}_{product_name[:30].replace(' ', '_')}.png", 
                f"No buy button found for {product_name}"
            )
            return False
        
        # Scroll to button with human-like behavior
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", buy_button)
        human_delay()
        
        # Take screenshot before clicking only if debug enabled
        if debug_screenshots:
            take_debug_screenshot(
                driver,
                f"before_click_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
                f"Before clicking buy button for {product_name}"
            )
        
        # Click the buy button with human-like interaction
        try:
            # Add small delay before clicking (like a human would)
            human_delay(0.2, 0.5)
            buy_button.click()
            print(f"[{datetime.now()}] Successfully clicked buy button for {product_name}")
        except Exception as e:
            # Try JavaScript click if regular click fails
            driver.execute_script("arguments[0].click();", buy_button)
            print(f"[{datetime.now()}] Used JavaScript click for buy button: {product_name}")
        
        # Human-like wait for page response - shorter but variable
        human_delay(1.0, 2.5)
        
        # Take screenshot after clicking only if debug enabled
        if debug_screenshots:
            take_debug_screenshot(
                driver,
                f"after_click_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
                f"After clicking buy button for {product_name}"
            )
        
        # Check if we were redirected to cart or checkout
        current_url = driver.current_url.lower()
        success_indicators = ["cart", "checkout", "order", "purchase", "payment"]
        
        if any(indicator in current_url for indicator in success_indicators):
            print(f"[{datetime.now()}] Purchase flow initiated for {product_name} - URL: {current_url}")
            if debug_screenshots:
                take_debug_screenshot(
                    driver,
                    f"purchase_success_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
                    f"Purchase flow initiated for {product_name}"
                )
            return True
        else:
            print(f"[{datetime.now()}] Purchase button clicked but no clear redirect for {product_name}")
            return True  # Still consider it a success as button was clicked
            
    except TimeoutException:
        print(f"[{datetime.now()}] Timeout while loading product page: {product_name}")
        # Always take screenshot on timeout for debugging
        take_debug_screenshot(
            driver,
            f"timeout_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
            f"Timeout loading page for {product_name}"
        )
        return False
        
    except Exception as e:
        print(f"[{datetime.now()}] Error attempting purchase for {product_name}: {str(e)}")
        # Always take screenshot on error for debugging
        take_debug_screenshot(
            driver,
            f"error_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
            f"Error during purchase attempt for {product_name}"
        )
        return False

def automate_purchases(available_products: List[Dict[str, Any]], headless: bool = True, debug_screenshots: bool = False) -> Dict[str, Any]:
    """
    Automate purchases for available products with optimized performance.
    
    Args:
        available_products (List[Dict]): List of available products to purchase
        headless (bool): Whether to run browser in headless mode
        debug_screenshots (bool): Whether to take debug screenshots (impacts performance)
        
    Returns:
        Dict: Results summary with success/failure counts and details
    """
    if not SELENIUM_AVAILABLE:
        print(f"[{datetime.now()}] Selenium not available - cannot automate purchases")
        return {
            "selenium_available": False,
            "total_products": len(available_products),
            "attempted": 0,
            "successful": 0,
            "failed": 0,
            "error": "Selenium not available"
        }
    
    if not available_products:
        print(f"[{datetime.now()}] No available products to purchase")
        return {
            "selenium_available": True,
            "total_products": 0,
            "attempted": 0,
            "successful": 0,
            "failed": 0
        }
    
    print(f"[{datetime.now()}] Starting optimized purchase automation for {len(available_products)} products")
    
    # Use optimized driver management for faster setup
    driver = get_or_create_driver(headless)
    if not driver:
        return {
            "selenium_available": True,
            "total_products": len(available_products),
            "attempted": 0,
            "successful": 0,
            "failed": len(available_products),
            "error": "Failed to initialize WebDriver"
        }
    
    results = {
        "selenium_available": True,
        "total_products": len(available_products),
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "details": []
    }
    
    try:
        for product in available_products:
            product_name = product.get("name", "Unknown Product")
            product_url = product.get("url")
            
            if not product_url:
                print(f"[{datetime.now()}] Skipping {product_name} - no URL available")
                results["failed"] += 1
                results["details"].append({
                    "product": product_name,
                    "success": False,
                    "reason": "No URL available"
                })
                continue
            
            results["attempted"] += 1
            
            success = attempt_purchase(driver, product_url, product_name, debug_screenshots)
            
            if success:
                results["successful"] += 1
                results["details"].append({
                    "product": product_name,
                    "success": True,
                    "url": product_url
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "product": product_name,
                    "success": False,
                    "reason": "Purchase attempt failed",
                    "url": product_url
                })
            
            # Human-like delay between product attempts
            if results["attempted"] < len(available_products):  # Don't delay after last product
                human_delay(BETWEEN_PRODUCTS_MIN_DELAY, BETWEEN_PRODUCTS_MAX_DELAY)
    
    finally:
        # Note: We keep the driver alive for potential reuse
        # It will be cleaned up when the process ends or explicitly called
        pass
    
    print(f"[{datetime.now()}] Purchase automation completed:")
    print(f"[{datetime.now()}] Total: {results['total_products']}, Attempted: {results['attempted']}, Successful: {results['successful']}, Failed: {results['failed']}")
    
    return results

if __name__ == "__main__":
    # Test with sample data if run directly
    sample_products = [
        {
            "name": "Test Product", 
            "url": "https://www.lazada.sg/products/test-i12345.html",
            "inStock": True
        }
    ]
    
    print("Testing selenium automation...")
    results = automate_purchases(sample_products, headless=False)
    print(f"Test results: {results}")