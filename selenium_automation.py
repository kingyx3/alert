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
DEFAULT_TIMEOUT = 30
SCREENSHOT_DIR = "screenshots"
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

def setup_chrome_driver(headless: bool = True) -> Optional[webdriver.Chrome]:
    """
    Set up Chrome WebDriver with appropriate options for automation.
    
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
            options.add_argument('--headless')
        
        # Security and compatibility options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        # User agent to avoid detection
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Window size for consistent screenshots
        options.add_argument('--window-size=1920,1080')
        
        # Disable notifications and popups
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        # Try to create driver
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(DEFAULT_TIMEOUT)
        
        print(f"[{datetime.now()}] Chrome WebDriver initialized successfully")
        return driver
        
    except Exception as e:
        print(f"[{datetime.now()}] Failed to initialize Chrome WebDriver: {str(e)}")
        return None

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

def attempt_purchase(driver: webdriver.Chrome, product_url: str, product_name: str) -> bool:
    """
    Attempt to purchase a product by clicking the buy button.
    
    Args:
        driver (webdriver.Chrome): WebDriver instance
        product_url (str): URL of the product page
        product_name (str): Name of the product for logging
        
    Returns:
        bool: True if purchase attempt was successful
    """
    timestamp = get_timestamp()
    
    try:
        print(f"[{datetime.now()}] Attempting to purchase: {product_name}")
        print(f"[{datetime.now()}] Navigating to: {product_url}")
        
        # Navigate to product page
        driver.get(product_url)
        
        # Take initial screenshot
        take_debug_screenshot(
            driver, 
            f"product_page_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
            f"Initial product page for {product_name}"
        )
        
        # Wait for page to load
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(2)  # Additional wait for dynamic content
        
        # Look for buy button
        buy_button = find_buy_button(driver)
        
        if not buy_button:
            take_debug_screenshot(
                driver,
                f"no_buy_button_{timestamp}_{product_name[:30].replace(' ', '_')}.png", 
                f"No buy button found for {product_name}"
            )
            return False
        
        # Scroll to button if needed
        driver.execute_script("arguments[0].scrollIntoView(true);", buy_button)
        time.sleep(1)
        
        # Take screenshot before clicking
        take_debug_screenshot(
            driver,
            f"before_click_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
            f"Before clicking buy button for {product_name}"
        )
        
        # Click the buy button
        try:
            buy_button.click()
            print(f"[{datetime.now()}] Successfully clicked buy button for {product_name}")
        except Exception as e:
            # Try JavaScript click if regular click fails
            driver.execute_script("arguments[0].click();", buy_button)
            print(f"[{datetime.now()}] Used JavaScript click for buy button: {product_name}")
        
        time.sleep(3)  # Wait for page response
        
        # Take screenshot after clicking
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
        take_debug_screenshot(
            driver,
            f"timeout_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
            f"Timeout loading page for {product_name}"
        )
        return False
        
    except Exception as e:
        print(f"[{datetime.now()}] Error attempting purchase for {product_name}: {str(e)}")
        take_debug_screenshot(
            driver,
            f"error_{timestamp}_{product_name[:30].replace(' ', '_')}.png",
            f"Error during purchase attempt for {product_name}"
        )
        return False

def automate_purchases(available_products: List[Dict[str, Any]], headless: bool = True) -> Dict[str, Any]:
    """
    Automate purchases for available products.
    
    Args:
        available_products (List[Dict]): List of available products to purchase
        headless (bool): Whether to run browser in headless mode
        
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
    
    print(f"[{datetime.now()}] Starting purchase automation for {len(available_products)} products")
    
    driver = setup_chrome_driver(headless)
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
            
            success = attempt_purchase(driver, product_url, product_name)
            
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
            
            # Small delay between attempts
            time.sleep(2)
    
    finally:
        # Always clean up the driver
        try:
            driver.quit()
            print(f"[{datetime.now()}] WebDriver closed successfully")
        except Exception as e:
            print(f"[{datetime.now()}] Error closing WebDriver: {str(e)}")
    
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