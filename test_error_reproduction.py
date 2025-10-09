#!/usr/bin/env python3
"""
Test script to reproduce the ETB_PRODUCT_SELECTORS error.
"""

import sys
import os

# Mock selenium since we don't need real browser for this test
class MockDriver:
    def __init__(self):
        pass
    
    def find_elements(self, *args):
        return []
    
    def get(self, url):
        pass
    
    def quit(self):
        pass

class MockWebDriverWait:
    def __init__(self, driver, timeout):
        pass
    
    def until(self, condition):
        # This will cause the ETB_PRODUCT_SELECTORS reference error
        raise Exception("Triggering the product selector loop")

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Monkey patch selenium imports to use our mocks
import scraper_intl
scraper_intl.WebDriverWait = MockWebDriverWait

# Create the product extractor
driver = MockDriver()
extractor = scraper_intl.ETBProductExtractor(driver)

# This should trigger the ETB_PRODUCT_SELECTORS error
try:
    result = extractor.wait_for_products_to_load(timeout=5)
    print("No error occurred - this is unexpected!")
except NameError as e:
    print(f"Successfully reproduced the error: {e}")
except Exception as e:
    print(f"Different error occurred: {e}")