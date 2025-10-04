#!/usr/bin/env python3

"""
Test script to verify SCRAPING_URL environment variable functionality
"""

import os
import sys
from scraper import BrowserScraper, Scraper

def test_scraping_url_functionality():
    """Test that SCRAPING_URL environment variable works correctly"""
    
    print("Testing SCRAPING_URL functionality...")
    print("=" * 50)
    
    # Test 1: Default behavior (no env var set)
    print("Test 1: Default behavior (no SCRAPING_URL set)")
    
    # Clear any existing env var
    if 'SCRAPING_URL' in os.environ:
        del os.environ['SCRAPING_URL']
    
    browser_scraper = BrowserScraper()
    scraper = Scraper()
    
    # Both should use default URLs (different ones for each class)
    assert browser_scraper.base_url.startswith('https://www.lazada.sg/pokemon-store'), \
        f"BrowserScraper should use default URL, got: {browser_scraper.base_url}"
    assert scraper.base_url.startswith('https://www.lazada.sg/pokemon-store'), \
        f"Scraper should use default URL, got: {scraper.base_url}"
    
    print("✓ Default URLs working correctly")
    
    # Test 2: Environment variable override
    print("\nTest 2: SCRAPING_URL environment variable override")
    
    test_url = "https://example.com/test-store"
    os.environ['SCRAPING_URL'] = test_url
    
    browser_scraper2 = BrowserScraper()
    scraper2 = Scraper()
    
    assert browser_scraper2.base_url == test_url, \
        f"BrowserScraper should use env var URL, got: {browser_scraper2.base_url}"
    assert scraper2.base_url == test_url, \
        f"Scraper should use env var URL, got: {scraper2.base_url}"
    
    print(f"✓ Environment variable override working: {test_url}")
    
    # Test 3: Direct parameter override
    print("\nTest 3: Direct parameter override")
    
    custom_url = "https://custom.example.com/products"
    
    browser_scraper3 = BrowserScraper(custom_url)
    scraper3 = Scraper(custom_url)
    
    assert browser_scraper3.base_url == custom_url, \
        f"BrowserScraper should use custom URL, got: {browser_scraper3.base_url}"
    assert scraper3.base_url == custom_url, \
        f"Scraper should use custom URL, got: {scraper3.base_url}"
    
    print(f"✓ Direct parameter override working: {custom_url}")
    
    # Test 4: Parameter takes precedence over environment variable
    print("\nTest 4: Parameter precedence over environment variable")
    
    # Env var is still set from test 2
    param_url = "https://param.example.com/override"
    
    browser_scraper4 = BrowserScraper(param_url)
    scraper4 = Scraper(param_url)
    
    assert browser_scraper4.base_url == param_url, \
        f"BrowserScraper parameter should override env var, got: {browser_scraper4.base_url}"
    assert scraper4.base_url == param_url, \
        f"Scraper parameter should override env var, got: {scraper4.base_url}"
    
    print(f"✓ Parameter precedence working: {param_url}")
    
    # Clean up
    if 'SCRAPING_URL' in os.environ:
        del os.environ['SCRAPING_URL']
    
    print("\n" + "=" * 50)
    print("All tests passed! SCRAPING_URL functionality working correctly.")
    return True

if __name__ == "__main__":
    try:
        success = test_scraping_url_functionality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)